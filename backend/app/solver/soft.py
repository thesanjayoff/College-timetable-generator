"""Soft-constraint objective terms. Each function adds (BoolVar, weight) pairs to
builder.objective_terms. Kept separate from model.py to make each term easy to find,
test and tune independently."""
from ortools.sat.python import cp_model


def add_soft_terms(builder) -> None:
    w = builder.weights
    _add_gap_penalties(builder, w)
    _add_same_subject_twice_penalty(builder, w)
    _add_section_daily_balance(builder, w)
    _add_teacher_workload_balance(builder, w)
    _add_teacher_preferences(builder, w)
    _add_lab_afternoon_preference(builder, w)
    _add_heavy_subject_last_period(builder, w)
    _add_stability(builder, w)


def _gap_vars_for_day(builder, occ_var_fn, entity_id: int, d: int, periods: list[int]):
    """Returns the per-period 'is a gap' bool vars for one entity on one day.

    A period i (strictly between the first and last occupied period) is a gap iff it is
    itself free, something is occupied before it, and something is occupied after it.
    """
    n = len(periods)
    if n < 3:
        return []  # no interior period exists to be a gap
    occ = [occ_var_fn(entity_id, d, p) for p in periods]

    before = [None] * n  # before[i] = True if anything occupied in occ[0..i-1]
    before[1] = occ[0]
    for i in range(2, n):
        b = builder.model.NewBoolVar(f"before_{entity_id}_{d}_{i}")
        builder.model.AddMaxEquality(b, [before[i - 1], occ[i - 1]])
        before[i] = b

    after = [None] * n  # after[i] = True if anything occupied in occ[i+1..n-1]
    after[n - 2] = occ[n - 1]
    for i in range(n - 3, -1, -1):
        a = builder.model.NewBoolVar(f"after_{entity_id}_{d}_{i}")
        builder.model.AddMaxEquality(a, [after[i + 1], occ[i + 1]])
        after[i] = a

    gaps = []
    for i in range(1, n - 1):
        b, a = before[i], after[i]
        g = builder.model.NewBoolVar(f"gap_{entity_id}_{d}_{periods[i]}")
        builder.model.Add(g <= b)
        builder.model.Add(g <= a)
        builder.model.Add(g + occ[i] <= 1)
        builder.model.Add(g >= b + a - occ[i] - 1)
        gaps.append(g)
    return gaps


def _add_gap_penalties(builder, w) -> None:
    grid = builder._any_grid()
    sec_weight = int(w.get("section_gaps", 0))
    tch_weight = int(w.get("teacher_gaps", 0))

    if sec_weight:
        section_ids = sorted({s for (s, _, _) in builder.section_slot_terms.keys()})
        for s in section_ids:
            for d in grid.day_indices:
                periods = grid.teaching_periods_for_day(d)
                for g in _gap_vars_for_day(builder, builder.section_occ_var, s, d, periods):
                    builder.objective_terms.append((g, sec_weight))

    if tch_weight:
        teacher_ids = sorted({t for (t, _, _) in builder.teacher_slot_terms.keys()})
        for t in teacher_ids:
            for d in grid.day_indices:
                periods = grid.teaching_periods_for_day(d)
                for g in _gap_vars_for_day(builder, builder.teacher_occ_var, t, d, periods):
                    builder.objective_terms.append((g, tch_weight))


def _add_same_subject_twice_penalty(builder, w) -> None:
    weight = int(w.get("same_subject_twice_a_day", 0))
    if not weight:
        return
    grid_cache = builder.grids
    for g in builder.data.groups:
        if g.max_per_day and g.max_per_day <= 1:
            continue  # already impossible, nothing to penalize
        if g.sessions_per_week <= 1:
            continue
        grid = grid_cache[g.time_structure_id]
        allowed_days = g.allowed_days if g.allowed_days is not None else tuple(grid.day_indices)
        for d in allowed_days:
            day_vars = []
            for occ in range(g.sessions_per_week):
                for (dd, p), var in builder.start_vars[(g.id, occ)].items():
                    if dd == d:
                        day_vars.append(var)
            if len(day_vars) <= 1:
                continue
            extra = builder.model.NewIntVar(0, len(day_vars), f"extra_{g.id}_{d}")
            builder.model.Add(extra >= sum(day_vars) - 1)
            builder.objective_terms.append((extra, weight))


def _add_section_daily_balance(builder, w) -> None:
    weight = int(w.get("section_daily_balance", 0))
    if not weight:
        return
    grid = builder._any_grid()
    section_ids = sorted({s for (s, _, _) in builder.section_slot_terms.keys()})
    for s in section_ids:
        totals = []
        for d in grid.day_indices:
            periods = grid.teaching_periods_for_day(d)
            terms = [builder.section_busy_expr(s, d, p) for p in periods if (s, d, p) in builder.section_slot_terms]
            total = builder.model.NewIntVar(0, len(periods) if periods else 1, f"secload_{s}_{d}")
            builder.model.Add(total == (sum(terms) if terms else 0))
            totals.append(total)
        if not totals:
            continue
        n_days = len(totals)
        total_sum = builder.model.NewIntVar(0, 200, f"secsum_{s}")
        builder.model.Add(total_sum == sum(totals))
        avg = builder.model.NewIntVar(0, 200, f"secavg_{s}")
        builder.model.AddDivisionEquality(avg, total_sum, n_days)
        for i, total in enumerate(totals):
            dev = builder.model.NewIntVar(0, 50, f"secdev_{s}_{i}")
            builder.model.Add(dev >= total - avg)
            builder.model.Add(dev >= avg - total)
            builder.objective_terms.append((dev, weight))


def _add_teacher_workload_balance(builder, w) -> None:
    weight = int(w.get("teacher_workload_balance", 0))
    if not weight:
        return
    grid = builder._any_grid()
    teacher_ids = sorted({t for (t, _, _) in builder.teacher_slot_terms.keys()})
    if len(teacher_ids) < 2:
        return
    weekly_totals = []
    for t in teacher_ids:
        terms = []
        for d in grid.day_indices:
            for p in grid.teaching_periods_for_day(d):
                if (t, d, p) in builder.teacher_slot_terms:
                    terms.append(builder.teacher_busy_expr(t, d, p))
        total = builder.model.NewIntVar(0, 60, f"tchload_{t}")
        builder.model.Add(total == (sum(terms) if terms else 0))
        weekly_totals.append(total)
    n = len(weekly_totals)
    total_sum = builder.model.NewIntVar(0, 3000, "tch_total_sum")
    builder.model.Add(total_sum == sum(weekly_totals))
    avg = builder.model.NewIntVar(0, 100, "tch_avg")
    builder.model.AddDivisionEquality(avg, total_sum, n)
    for i, total in enumerate(weekly_totals):
        dev = builder.model.NewIntVar(0, 100, f"tchdev_{i}")
        builder.model.Add(dev >= total - avg)
        builder.model.Add(dev >= avg - total)
        builder.objective_terms.append((dev, weight))


def _add_teacher_preferences(builder, w) -> None:
    grid = builder._any_grid()
    for pref in builder.data.teacher_preferences:
        t = pref["teacher_id"]
        ptype = pref["type"]
        weight_key = {
            "preferred_day": "teacher_preferred_day",
            "free_day": "teacher_free_day",
            "no_first_period": "teacher_no_first_period",
            "no_last_period": "teacher_no_last_period",
            "avoid_back_to_back": "teacher_avoid_back_to_back",
        }.get(ptype)
        if weight_key is None:
            continue
        weight = int(round(w.get(weight_key, 0) * pref.get("weight", 1.0)))
        if not weight:
            continue

        if ptype == "free_day":
            d = pref["day_index"]
            for p in grid.teaching_periods_for_day(d):
                if (t, d, p) in builder.teacher_slot_terms:
                    builder.objective_terms.append((builder.teacher_occ_var(t, d, p), weight))

        elif ptype == "preferred_day":
            preferred = pref["day_index"]
            for d in grid.day_indices:
                if d == preferred:
                    continue
                for p in grid.teaching_periods_for_day(d):
                    if (t, d, p) in builder.teacher_slot_terms:
                        builder.objective_terms.append((builder.teacher_occ_var(t, d, p), weight))

        elif ptype == "no_first_period":
            for d in grid.day_indices:
                p = grid.first_teaching_period(d)
                if p is not None and (t, d, p) in builder.teacher_slot_terms:
                    builder.objective_terms.append((builder.teacher_occ_var(t, d, p), weight))

        elif ptype == "no_last_period":
            for d in grid.day_indices:
                p = grid.last_teaching_period(d)
                if p is not None and (t, d, p) in builder.teacher_slot_terms:
                    builder.objective_terms.append((builder.teacher_occ_var(t, d, p), weight))

        elif ptype == "avoid_back_to_back":
            for d in grid.day_indices:
                periods = grid.teaching_periods_for_day(d)
                for i in range(len(periods) - 1):
                    p1, p2 = periods[i], periods[i + 1]
                    if p2 != p1 + 1:
                        continue
                    if (t, d, p1) not in builder.teacher_slot_terms or (t, d, p2) not in builder.teacher_slot_terms:
                        continue
                    both = builder.model.NewBoolVar(f"b2b_{t}_{d}_{p1}")
                    o1, o2 = builder.teacher_occ_var(t, d, p1), builder.teacher_occ_var(t, d, p2)
                    builder.model.AddMultiplicationEquality(both, [o1, o2])
                    builder.objective_terms.append((both, weight))


def _add_lab_afternoon_preference(builder, w) -> None:
    weight = int(w.get("lab_afternoon_preference", 0))
    if not weight:
        return
    for g in builder.data.groups:
        if not g.prefer_afternoon:
            continue
        cutoff = g.afternoon_cutoff_period
        if cutoff is None:
            continue
        for occ in range(g.sessions_per_week):
            for (d, p), var in builder.start_vars[(g.id, occ)].items():
                if p < cutoff:
                    builder.objective_terms.append((var, weight))


def _add_heavy_subject_last_period(builder, w) -> None:
    weight = int(w.get("heavy_subject_last_period", 0))
    if not weight:
        return
    grid_cache = builder.grids
    for g in builder.data.groups:
        if not g.avoid_last_period:
            continue
        grid = grid_cache[g.time_structure_id]
        for occ in range(g.sessions_per_week):
            for (d, p), var in builder.start_vars[(g.id, occ)].items():
                last = grid.last_teaching_period(d)
                if last is not None and p + g.block_size - 1 >= last:
                    builder.objective_terms.append((var, weight))


def _add_stability(builder, w) -> None:
    weight = int(w.get("stability", 0) * builder.stability_weight)
    if not weight:
        return
    for (gid, occ), prev in builder._previous_index.items():
        start_vars = builder.start_vars.get((gid, occ))
        if not start_vars:
            continue
        same_var = start_vars.get((prev.day_index, prev.period_index))
        if same_var is None:
            # previous slot no longer valid at all -> fully penalized (moved)
            builder.objective_terms.extend((v, weight) for v in start_vars.values())
            continue
        moved = builder.model.NewBoolVar(f"moved_{gid}_{occ}")
        builder.model.Add(moved == 1 - same_var)
        builder.objective_terms.append((moved, weight))
