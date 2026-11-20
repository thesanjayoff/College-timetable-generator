"""Builds a CP-SAT model from a SolverInput. Pure function of the IR -- no DB access here,
which keeps this unit-testable with small hand-built instances."""
from dataclasses import dataclass, field

from ortools.sat.python import cp_model

from app.solver.grid import TimeGrid
from app.solver.ir import SolverInput, RequirementGroup, ReqPart

BIG_M = 100_000


@dataclass
class BuiltModel:
    model: cp_model.CpModel
    # (group_id, occurrence) -> {(day, period): BoolVar}
    start_vars: dict[tuple[str, int], dict[tuple[int, int], cp_model.IntVar]]
    # (group_id, occurrence) -> BoolVar (true if this occurrence could not be placed)
    unplaced_vars: dict[tuple[str, int], cp_model.IntVar]
    # (group_id, occurrence, part_key) -> {teacher_id: BoolVar}
    teacher_vars: dict[tuple[str, int, str], dict[int, cp_model.IntVar]]
    # (group_id, occurrence, part_key) -> {room_id: BoolVar}
    room_vars: dict[tuple[str, int, str], dict[int, cp_model.IntVar]]
    groups_by_id: dict[str, RequirementGroup]
    objective_terms: list[tuple[cp_model.IntVar, int]] = field(default_factory=list)


def _contiguous_runs(periods: list[int]) -> list[list[int]]:
    if not periods:
        return []
    periods = sorted(periods)
    runs, current = [], [periods[0]]
    for p in periods[1:]:
        if p == current[-1] + 1:
            current.append(p)
        else:
            runs.append(current)
            current = [p]
    runs.append(current)
    return runs


class ModelBuilder:
    def __init__(self, data: SolverInput, weights: dict[str, float], stability_weight: float = 0.0):
        self.data = data
        self.weights = weights
        self.stability_weight = stability_weight
        self.model = cp_model.CpModel()
        self.grids: dict[int, TimeGrid] = data.time_structures

        self.start_vars: dict[tuple[str, int], dict[tuple[int, int], cp_model.IntVar]] = {}
        self.unplaced_vars: dict[tuple[str, int], cp_model.IntVar] = {}
        self.teacher_vars: dict[tuple[str, int, str], dict[int, cp_model.IntVar]] = {}
        self.room_vars: dict[tuple[str, int, str], dict[int, cp_model.IntVar]] = {}
        self.groups_by_id = {g.id: g for g in data.groups}

        # resource -> list of (expr term contributing 0/1 occupancy)
        self.teacher_slot_terms: dict[tuple[int, int, int], list] = {}
        self.room_slot_terms: dict[tuple[int, int, int], list] = {}
        self.section_slot_terms: dict[tuple[int, int, int], list] = {}

        self.objective_terms: list[tuple[cp_model.IntVar, int]] = []
        self._occ_var_cache: dict[tuple[str, int, int, int], cp_model.IntVar] = {}

        self._locks_index = {
            (lk.group_id, lk.occurrence): lk for lk in data.locks
        }
        self._previous_index = {
            (p.group_id, p.occurrence): p for p in data.previous
        }

    # ------------------------------------------------------------------ build
    def build(self) -> BuiltModel:
        for g in self.data.groups:
            self._build_group(g)
        self._add_resource_conflict_constraints()
        self._add_teacher_load_constraints()
        self._add_section_load_constraints()
        self._add_objective()
        return BuiltModel(
            model=self.model,
            start_vars=self.start_vars,
            unplaced_vars=self.unplaced_vars,
            teacher_vars=self.teacher_vars,
            room_vars=self.room_vars,
            groups_by_id=self.groups_by_id,
            objective_terms=self.objective_terms,
        )

    # ------------------------------------------------------------ one group
    def _build_group(self, g: RequirementGroup):
        grid = self.grids[g.time_structure_id]
        allowed_days = g.allowed_days if g.allowed_days is not None else tuple(grid.day_indices)

        # Candidate (day, start_period) combos valid for this group's block size.
        domain: list[tuple[int, int]] = []
        for d in allowed_days:
            for p in grid.valid_block_starts(d, g.block_size):
                domain.append((d, p))

        for occ in range(g.sessions_per_week):
            lock = self._locks_index.get((g.id, occ))
            occ_domain = domain
            if lock is not None:
                occ_domain = [(lock.day_index, lock.period_index)]

            start_vars: dict[tuple[int, int], cp_model.IntVar] = {}
            for (d, p) in occ_domain:
                # Filter out combos that violate a FIXED resource's hard availability.
                if self._fixed_resource_blocked(g, d, p):
                    continue
                var = self.model.NewBoolVar(f"start_{g.id}_{occ}_{d}_{p}")
                start_vars[(d, p)] = var

            unplaced = self.model.NewBoolVar(f"unplaced_{g.id}_{occ}")
            if lock is not None and not start_vars:
                # A lock must always be placeable; if filtered out, something upstream is wrong.
                raise ValueError(f"Locked session for group {g.id} occ {occ} is infeasible given availability")

            self.model.Add(sum(start_vars.values()) + unplaced == 1)
            if lock is not None:
                self.model.Add(unplaced == 0)

            self.start_vars[(g.id, occ)] = start_vars
            self.unplaced_vars[(g.id, occ)] = unplaced
            self.objective_terms.append((unplaced, BIG_M))

            # Per-part teacher/room choice vars.
            for part in g.parts:
                self._build_part_choice(g, occ, part, start_vars, lock)

            # Register section occupancy terms for every covered period.
            for (d, p) in start_vars:
                var = start_vars[(d, p)]
                for k in range(g.block_size):
                    period = p + k
                    for sec in g.occupied_section_ids:
                        self.section_slot_terms.setdefault((sec, d, period), []).append(var)

        # Hard cap: at most max_per_day occurrences of this group's subject on one day (per section group).
        if g.max_per_day is not None and g.sessions_per_week > 1:
            for d in allowed_days:
                terms = []
                for occ in range(g.sessions_per_week):
                    for (dd, p), var in self.start_vars[(g.id, occ)].items():
                        if dd == d:
                            terms.append(var)
                if terms:
                    self.model.Add(sum(terms) <= g.max_per_day)

    def _fixed_resource_blocked(self, g: RequirementGroup, d: int, p: int) -> bool:
        for part in g.parts:
            if part.is_fixed_teacher and part.teacher_options:
                t = part.teacher_options[0]
                if self._teacher_unavailable_in_block(t, d, p, g.block_size):
                    return True
                allowed = self.data.teacher_visiting_days.get(t)
                if allowed is not None and d not in allowed:
                    return True
            if part.is_fixed_room and part.room_options:
                r = part.room_options[0]
                for k in range(g.block_size):
                    if (r, d, p + k) in self.data.room_unavailable:
                        return True
        return False

    def _teacher_unavailable_in_block(self, teacher_id: int, d: int, p: int, block_size: int) -> bool:
        if (teacher_id, d) in self.data.teacher_day_off:
            return True
        for k in range(block_size):
            if (teacher_id, d, p + k) in self.data.teacher_unavailable:
                return True
        return False

    def _build_part_choice(self, g: RequirementGroup, occ: int, part: ReqPart,
                            start_vars: dict[tuple[int, int], cp_model.IntVar], lock) -> None:
        key = (g.id, occ, part.key)

        teacher_options = list(part.teacher_options) or [None]
        tvars: dict[int, cp_model.IntVar] = {}
        for t in teacher_options:
            if t is None:
                continue
            tvars[t] = self.model.NewBoolVar(f"tch_{g.id}_{occ}_{part.key}_{t}")
        if tvars:
            self.model.AddExactlyOne(list(tvars.values()))
        self.teacher_vars[key] = tvars

        room_options = list(part.room_options) or [None]
        rvars: dict[int, cp_model.IntVar] = {}
        for r in room_options:
            if r is None:
                continue
            rvars[r] = self.model.NewBoolVar(f"room_{g.id}_{occ}_{part.key}_{r}")
        if rvars:
            self.model.AddExactlyOne(list(rvars.values()))
        self.room_vars[key] = rvars

        if lock is not None:
            lt, lr = lock.part_assignments.get(part.key, (None, None))
            if lt is not None and lt in tvars:
                self.model.Add(tvars[lt] == 1)
            if lr is not None and lr in rvars:
                self.model.Add(rvars[lr] == 1)

        fixed_teacher = part.is_fixed_teacher and len(tvars) <= 1
        fixed_room = part.is_fixed_room and len(rvars) <= 1

        for (d, p), xvar in start_vars.items():
            for k in range(g.block_size):
                period = p + k
                # Teacher occupancy contribution.
                if tvars:
                    if fixed_teacher:
                        t = next(iter(tvars))
                        self.teacher_slot_terms.setdefault((t, d, period), []).append(xvar)
                    else:
                        for t, tv in tvars.items():
                            if self._teacher_unavailable_in_block(t, d, p, g.block_size):
                                self.model.AddBoolOr([xvar.Not(), tv.Not()])
                                continue
                            allowed = self.data.teacher_visiting_days.get(t)
                            if allowed is not None and d not in allowed:
                                self.model.AddBoolOr([xvar.Not(), tv.Not()])
                                continue
                            and_var = self.model.NewBoolVar(f"and_t_{g.id}_{occ}_{part.key}_{t}_{d}_{p}_{k}")
                            self.model.AddMultiplicationEquality(and_var, [xvar, tv])
                            self.teacher_slot_terms.setdefault((t, d, period), []).append(and_var)
                # Room occupancy contribution.
                if rvars:
                    if fixed_room:
                        r = next(iter(rvars))
                        self.room_slot_terms.setdefault((r, d, period), []).append(xvar)
                    else:
                        for r, rv in rvars.items():
                            if (r, d, period) in self.data.room_unavailable:
                                self.model.AddBoolOr([xvar.Not(), rv.Not()])
                                continue
                            and_var = self.model.NewBoolVar(f"and_r_{g.id}_{occ}_{part.key}_{r}_{d}_{p}_{k}")
                            self.model.AddMultiplicationEquality(and_var, [xvar, rv])
                            self.room_slot_terms.setdefault((r, d, period), []).append(and_var)

    # ------------------------------------------------------------- resources
    def _add_resource_conflict_constraints(self):
        for _, terms in self.teacher_slot_terms.items():
            if len(terms) > 1:
                self.model.Add(sum(terms) <= 1)
        for _, terms in self.room_slot_terms.items():
            if len(terms) > 1:
                self.model.Add(sum(terms) <= 1)
        for _, terms in self.section_slot_terms.items():
            if len(terms) > 1:
                self.model.Add(sum(terms) <= 1)

    def _occ_expr(self, table: dict, key) -> int | cp_model.LinearExpr:
        terms = table.get(key)
        if not terms:
            return 0
        if len(terms) == 1:
            return terms[0]
        return sum(terms)

    def teacher_busy_expr(self, teacher_id: int, d: int, p: int):
        return self._occ_expr(self.teacher_slot_terms, (teacher_id, d, p))

    def section_busy_expr(self, section_id: int, d: int, p: int):
        return self._occ_expr(self.section_slot_terms, (section_id, d, p))

    def _materialized_occ_var(self, kind: str, entity_id: int, d: int, p: int,
                               table: dict) -> cp_model.IntVar:
        cache_key = (kind, entity_id, d, p)
        if cache_key in self._occ_var_cache:
            return self._occ_var_cache[cache_key]
        terms = table.get((entity_id, d, p), [])
        var = self.model.NewBoolVar(f"occ_{kind}_{entity_id}_{d}_{p}")
        if terms:
            self.model.Add(var == sum(terms))
        else:
            self.model.Add(var == 0)
        self._occ_var_cache[cache_key] = var
        return var

    def section_occ_var(self, section_id: int, d: int, p: int) -> cp_model.IntVar:
        return self._materialized_occ_var("sec", section_id, d, p, self.section_slot_terms)

    def teacher_occ_var(self, teacher_id: int, d: int, p: int) -> cp_model.IntVar:
        return self._materialized_occ_var("tch", teacher_id, d, p, self.teacher_slot_terms)

    # --------------------------------------------------------- teacher load
    def _add_teacher_load_constraints(self):
        teacher_ids = {t for (t, _, _) in self.teacher_slot_terms.keys()}
        for t in teacher_ids:
            grid = self._any_grid()
            max_day = self.data.teacher_max_per_day.get(t)
            max_week = self.data.teacher_max_per_week.get(t)
            max_consec = self.data.teacher_max_consecutive.get(t)
            week_terms = []
            for d in grid.day_indices:
                periods = grid.teaching_periods_for_day(d)
                day_terms = [self.teacher_busy_expr(t, d, p) for p in periods if (t, d, p) in self.teacher_slot_terms]
                if max_day is not None and day_terms:
                    self.model.Add(sum(day_terms) <= max_day)
                week_terms.extend(day_terms)
                if max_consec is not None:
                    for run in _contiguous_runs(periods):
                        window = max_consec + 1
                        if len(run) <= max_consec:
                            continue
                        for i in range(len(run) - window + 1):
                            win_terms = [self.teacher_busy_expr(t, d, run[i + j]) for j in range(window)]
                            win_terms = [w for w in win_terms if w is not None]
                            if win_terms:
                                self.model.Add(sum(win_terms) <= max_consec)
            if max_week is not None and week_terms:
                self.model.Add(sum(week_terms) <= max_week)

    # --------------------------------------------------------- section load
    def _add_section_load_constraints(self):
        section_ids = {s for (s, _, _) in self.section_slot_terms.keys()}
        for s in section_ids:
            max_day = self.data.section_max_per_day.get(s)
            max_consec = self.data.section_max_consecutive.get(s)
            if max_day is None and max_consec is None:
                continue
            grid = self._any_grid()
            for d in grid.day_indices:
                periods = grid.teaching_periods_for_day(d)
                day_terms = [self.section_busy_expr(s, d, p) for p in periods if (s, d, p) in self.section_slot_terms]
                if max_day is not None and day_terms:
                    self.model.Add(sum(day_terms) <= max_day)
                if max_consec is not None:
                    for run in _contiguous_runs(periods):
                        window = max_consec + 1
                        if len(run) <= max_consec:
                            continue
                        for i in range(len(run) - window + 1):
                            win_terms = [self.section_busy_expr(s, d, run[i + j]) for j in range(window)]
                            win_terms = [w for w in win_terms if w is not None]
                            if win_terms:
                                self.model.Add(sum(win_terms) <= max_consec)

    def _any_grid(self) -> TimeGrid:
        return next(iter(self.grids.values()))

    # ------------------------------------------------------------ objective
    def _add_objective(self):
        from app.solver.soft import add_soft_terms
        add_soft_terms(self)
        total = sum(var * weight for var, weight in self.objective_terms)
        self.model.Minimize(total)
