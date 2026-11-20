"""Smoke test for the CP-SAT model builder using a tiny hand-built instance,
independent of the database."""
from dataclasses import dataclass

from ortools.sat.python import cp_model

from app.models.enums import PeriodKind, RoomType
from app.solver.grid import TimeGrid
from app.solver.ir import ReqPart, RequirementGroup, SolverInput
from app.solver.model import ModelBuilder


@dataclass
class FakeDay:
    day_index: int
    name: str
    max_period_index: int | None


@dataclass
class FakePeriod:
    period_index: int
    kind: PeriodKind
    teaching_order: int | None


@dataclass
class FakeStructure:
    id: int
    days: list
    periods: list


def make_grid() -> TimeGrid:
    days = [FakeDay(i, name, None) for i, name in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri"])]
    periods = []
    idx = 0
    for slot in range(6):
        periods.append(FakePeriod(idx, PeriodKind.TEACHING, slot))
        idx += 1
        if slot == 2:
            periods.append(FakePeriod(idx, PeriodKind.BREAK, None))
            idx += 1
    structure = FakeStructure(id=1, days=days, periods=periods)
    return TimeGrid(structure)


def test_tiny_feasible_instance():
    grid = make_grid()

    part_math = ReqPart(
        key="main", subject_id=1, teacher_options=(1,), is_fixed_teacher=True,
        room_type_required=RoomType.CLASSROOM, capacity_required=40, room_options=(1,), is_fixed_room=True,
    )
    part_phy = ReqPart(
        key="main", subject_id=2, teacher_options=(2,), is_fixed_teacher=True,
        room_type_required=RoomType.CLASSROOM, capacity_required=40, room_options=(1,), is_fixed_room=True,
    )
    g1 = RequirementGroup(
        id="g1", kind="regular", label="Math-A", subject_id=1, occupied_section_ids=(100,),
        parts=(part_math,), sessions_per_week=3, block_size=1, spread_across_days=True,
        max_per_day=1, time_structure_id=1,
    )
    g2 = RequirementGroup(
        id="g2", kind="regular", label="Physics-A", subject_id=2, occupied_section_ids=(100,),
        parts=(part_phy,), sessions_per_week=2, block_size=1, spread_across_days=True,
        max_per_day=1, time_structure_id=1,
    )

    data = SolverInput(
        groups=[g1, g2],
        time_structures={1: grid},
        teacher_unavailable=set(),
    )

    builder = ModelBuilder(data, weights={"section_gaps": 10, "teacher_gaps": 5}, stability_weight=0)
    built = builder.build()

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10
    solver.parameters.num_search_workers = 1
    status = solver.Solve(built.model)

    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE), solver.StatusName(status)

    # No unplaced sessions in this trivially feasible instance.
    for key, var in built.unplaced_vars.items():
        assert solver.Value(var) == 0, f"{key} was left unplaced"

    # Each occurrence placed exactly once, and section never double-booked.
    placements = []
    for (gid, occ), svars in built.start_vars.items():
        chosen = [(d, p) for (d, p), v in svars.items() if solver.Value(v) == 1]
        assert len(chosen) == 1
        placements.append((gid, occ, chosen[0]))

    seen_slots = {}
    for gid, occ, (d, p) in placements:
        seen_slots.setdefault((d, p), []).append((gid, occ))
    for slot, items in seen_slots.items():
        assert len(items) == 1, f"double booking at {slot}: {items}"

    print("placements:", placements)


def test_lab_block_and_teacher_choice():
    grid = make_grid()

    batch1 = ReqPart(
        key="A1", subject_id=3, teacher_options=(10, 11), is_fixed_teacher=False,
        room_type_required=RoomType.LAB, capacity_required=20, room_options=(50,), is_fixed_room=True,
    )
    batch2 = ReqPart(
        key="A2", subject_id=3, teacher_options=(10, 11), is_fixed_teacher=False,
        room_type_required=RoomType.LAB, capacity_required=20, room_options=(51,), is_fixed_room=True,
    )
    lab_group = RequirementGroup(
        id="lab1", kind="lab", label="CS-Lab-A", subject_id=3, occupied_section_ids=(200,),
        parts=(batch1, batch2), sessions_per_week=1, block_size=2, spread_across_days=True,
        max_per_day=1, time_structure_id=1,
    )

    data = SolverInput(groups=[lab_group], time_structures={1: grid}, teacher_unavailable=set())
    builder = ModelBuilder(data, weights={}, stability_weight=0)
    built = builder.build()

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10
    solver.parameters.num_search_workers = 1
    status = solver.Solve(built.model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE), solver.StatusName(status)

    (d, p), = [(dd, pp) for (dd, pp), v in built.start_vars[("lab1", 0)].items() if solver.Value(v) == 1]
    # Block must not straddle the break which sits right after teaching-period index 2.
    assert not (p <= 2 < p + 2 and p != 2), f"lab block {p}..{p+1} straddles the break"

    t1 = [t for t, v in built.teacher_vars[("lab1", 0, "A1")].items() if solver.Value(v) == 1][0]
    t2 = [t for t, v in built.teacher_vars[("lab1", 0, "A2")].items() if solver.Value(v) == 1][0]
    assert t1 != t2, "both lab batches got the same teacher at the same time"
    print("lab placement:", d, p, "teachers", t1, t2)


if __name__ == "__main__":
    test_tiny_feasible_instance()
    test_lab_block_and_teacher_choice()
    print("OK")
