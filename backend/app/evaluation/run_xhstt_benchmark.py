"""Converts a real public XHSTT benchmark instance, solves it with this project's CP-SAT
model, and re-checks the result with the independent verifier -- all without touching a
database (both the solver IR and the verifier's VerifierInput are DB-independent, so a
converted instance can be run through the exact same machinery as everything else).

Usage: python -m app.evaluation.run_xhstt_benchmark <path-to-xhstt.xml> [time_limit_seconds]
"""
import json
import sys
import time

from app.evaluation.xhstt_converter import convert_xhstt_instance
from app.solver.service import SolveConfig, solve
from app.verifier.checks import check_all
from app.verifier.types import (
    VDayInfo, VPeriodInfo, VSession, VSubjectReq, VTeacherInfo, VTimeStructure, VerifierInput,
)


def build_verifier_input(solver_input, result) -> VerifierInput:
    structures: dict[int, VTimeStructure] = {}
    for sid, grid in solver_input.time_structures.items():
        days = [VDayInfo(d.day_index, grid.max_period_for_day(d.day_index)) for d in grid.days]
        periods = [VPeriodInfo(p.period_index, grid.is_teaching(p.period_index)) for p in grid.periods]
        structures[sid] = VTimeStructure(id=sid, days=days, periods=periods)

    teachers: dict[int, VTeacherInfo] = {}
    for tid, dp in solver_input.teacher_max_per_day.items():
        teachers.setdefault(tid, VTeacherInfo(id=tid, max_periods_per_day=None, max_periods_per_week=None,
                                               max_consecutive_periods=None))
        teachers[tid].max_periods_per_day = dp
    for (tid, day, period) in solver_input.teacher_unavailable:
        t = teachers.setdefault(tid, VTeacherInfo(id=tid, max_periods_per_day=None, max_periods_per_week=None,
                                                   max_consecutive_periods=None))
        t.unavailable_slots.add((day, period))

    sessions: list[VSession] = []
    req_counts: dict[tuple[int, int], dict] = {}
    group_by_id = {g.id: g for g in solver_input.groups}

    for i, s in enumerate(result.sessions):
        part = s.parts[0]
        section_id = s.occupied_section_ids[0] if s.occupied_section_ids else None
        sessions.append(VSession(
            id=i, sync_group=None, day_index=s.day_index, period_index=s.period_index,
            num_periods=s.num_periods, subject_id=part.subject_id, teacher_id=part.teacher_id,
            room_id=part.room_id, lab_batch_id=None, section_ids=s.occupied_section_ids, kind="regular",
        ))
        if section_id is not None:
            key = (part.subject_id, section_id)
            req_counts.setdefault(key, {"count": 0, "block_size": s.num_periods})
            req_counts[key]["count"] += 1

    requirements = [
        VSubjectReq(subject_id=subj, section_id=sec, sessions_per_week=info["count"],
                    block_size=info["block_size"], max_per_day=99, is_lab=False,
                    avoid_last_period=False, prefer_afternoon=False)
        for (subj, sec), info in req_counts.items()
    ]

    return VerifierInput(
        sessions=sessions, requirements=requirements, structures=structures, teachers=teachers,
        rooms={}, sections={}, expected_combined={}, expected_elective={},
    )


def main():
    xml_path = sys.argv[1] if len(sys.argv) > 1 else "data/benchmarks/NetherlandsKottenpark2008.xml"
    time_limit = float(sys.argv[2]) if len(sys.argv) > 2 else 120.0

    t0 = time.time()
    solver_input, report = convert_xhstt_instance(xml_path)
    convert_time = time.time() - t0
    print(f"Converted: {report}", file=sys.stderr)

    config = SolveConfig(time_limit_seconds=time_limit, num_workers=8, deterministic=False, random_seed=1)
    weights = {"section_gaps": 1, "teacher_gaps": 1}
    t0 = time.time()
    result = solve(solver_input, weights, config)
    solve_time = time.time() - t0

    verifier_input = build_verifier_input(solver_input, result)
    violations = check_all(verifier_input)
    by_category: dict[str, int] = {}
    for v in violations:
        by_category[v.category] = by_category.get(v.category, 0) + 1

    out = {
        "instance": report.instance_name, "num_events": report.num_events,
        "num_teachers": report.num_teachers, "num_rooms": report.num_rooms, "num_classes": report.num_classes,
        "convert_time_s": round(convert_time, 3), "solve_time_s": round(solve_time, 3),
        "solve_status": result.status, "unplaced_count": len(result.unplaced),
        "placed_count": len(result.sessions), "objective_value": result.objective_value,
        "best_bound": result.best_bound,
        "verifier_hard_violations": len(violations), "verifier_violations_by_category": by_category,
        "converter_notes": {
            "events_with_no_teacher": report.events_with_no_teacher,
            "events_with_multi_teacher_only_primary_tracked": report.events_with_multi_teacher,
            "events_with_unresolved_room_fallback": report.events_with_unresolved_room,
        },
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
