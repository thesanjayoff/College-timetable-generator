"""Orchestrates a solve: builds the CP-SAT model from a SolverInput, runs it with a time
budget and progress reporting, and extracts a plain-data result. No DB access here."""
import threading
from dataclasses import dataclass, field
from typing import Callable

from ortools.sat.python import cp_model

from app.solver.ir import SolverInput
from app.solver.model import ModelBuilder, BuiltModel


@dataclass
class SolveConfig:
    time_limit_seconds: float = 60.0
    num_workers: int = 8
    random_seed: int | None = None
    deterministic: bool = False
    stability_weight: float = 0.0


@dataclass
class ProgressInfo:
    elapsed_seconds: float
    objective_value: float
    best_bound: float
    solutions_found: int


@dataclass
class PartAssignment:
    part_key: str
    subject_id: int
    teacher_id: int | None
    room_id: int | None
    lab_batch_id: int | None


@dataclass
class SessionOut:
    group_id: str
    kind: str
    occurrence: int
    day_index: int
    period_index: int
    num_periods: int
    occupied_section_ids: tuple[int, ...]
    parts: list[PartAssignment]
    source_ref: dict


@dataclass
class UnplacedOut:
    group_id: str
    occurrence: int
    label: str
    source_ref: dict


@dataclass
class SolveResult:
    status: str
    sessions: list[SessionOut] = field(default_factory=list)
    unplaced: list[UnplacedOut] = field(default_factory=list)
    objective_value: float = 0.0
    best_bound: float = 0.0
    wall_time: float = 0.0
    is_feasible: bool = False


class _ProgressCallback(cp_model.CpSolverSolutionCallback):
    def __init__(self, on_progress: Callable[[ProgressInfo], None] | None, stop_event: threading.Event | None):
        super().__init__()
        self._on_progress = on_progress
        self._stop_event = stop_event
        self.solutions_found = 0

    def on_solution_callback(self):
        self.solutions_found += 1
        if self._on_progress is not None:
            self._on_progress(ProgressInfo(
                elapsed_seconds=self.WallTime(),
                objective_value=self.ObjectiveValue(),
                best_bound=self.BestObjectiveBound(),
                solutions_found=self.solutions_found,
            ))
        if self._stop_event is not None and self._stop_event.is_set():
            self.StopSearch()


def solve(
    data: SolverInput,
    weights: dict[str, float],
    config: SolveConfig,
    on_progress: Callable[[ProgressInfo], None] | None = None,
    stop_event: threading.Event | None = None,
) -> SolveResult:
    builder = ModelBuilder(data, weights, stability_weight=config.stability_weight)
    built = builder.build()

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = config.time_limit_seconds
    solver.parameters.num_search_workers = 1 if config.deterministic else max(1, config.num_workers)
    if config.random_seed is not None:
        solver.parameters.random_seed = config.random_seed
    solver.parameters.enumerate_all_solutions = False

    callback = _ProgressCallback(on_progress, stop_event)
    status = solver.Solve(built.model, callback)

    result = SolveResult(status=solver.StatusName(status))
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return result

    result.is_feasible = True
    result.objective_value = solver.ObjectiveValue()
    result.best_bound = solver.BestObjectiveBound()
    result.wall_time = solver.WallTime()

    _extract(built, solver, result)
    return result


def _extract(built: BuiltModel, solver: cp_model.CpSolver, result: SolveResult) -> None:
    for (gid, occ), svars in built.start_vars.items():
        group = built.groups_by_id[gid]
        unplaced_var = built.unplaced_vars[(gid, occ)]
        if solver.Value(unplaced_var) == 1:
            result.unplaced.append(UnplacedOut(
                group_id=gid, occurrence=occ, label=group.label, source_ref=group.source_ref,
            ))
            continue
        chosen = [(d, p) for (d, p), v in svars.items() if solver.Value(v) == 1]
        if not chosen:
            continue
        d, p = chosen[0]
        parts_out = []
        for part in group.parts:
            tvars = built.teacher_vars.get((gid, occ, part.key), {})
            rvars = built.room_vars.get((gid, occ, part.key), {})
            teacher_id = next((t for t, v in tvars.items() if solver.Value(v) == 1), None)
            room_id = next((r for r, v in rvars.items() if solver.Value(v) == 1), None)
            parts_out.append(PartAssignment(
                part_key=part.key, subject_id=part.subject_id, teacher_id=teacher_id,
                room_id=room_id, lab_batch_id=part.lab_batch_id,
            ))
        result.sessions.append(SessionOut(
            group_id=gid, kind=group.kind, occurrence=occ, day_index=d, period_index=p,
            num_periods=group.block_size, occupied_section_ids=group.occupied_section_ids,
            parts=parts_out, source_ref=group.source_ref,
        ))
