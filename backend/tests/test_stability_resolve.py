"""Minimal-change re-solving: after a small disruption (one teacher goes unavailable on
one day), solving with the stability weight on should move fewer sessions than solving
with it off."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
import app.models  # noqa
from app.models.teacher import TeacherUnavailability
from app.models.timetable import TimetableVersion
from app.solver.builder import _group_id_for_session, build_solver_input
from app.solver.service import SolveConfig, solve
from app.services.persist import persist_solve_result
from tests.test_integration_small import seed


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def occurrence_slots(db, version_id) -> dict[str, list[tuple[int, int]]]:
    from app.models.timetable import TimetableSession
    rows = db.query(TimetableSession).filter(TimetableSession.version_id == version_id).all()
    by_group: dict[str, list[tuple[int, int]]] = {}
    for r in rows:
        gid = _group_id_for_session(r)
        if gid:
            by_group.setdefault(gid, []).append((r.day_index, r.period_index))
    return {gid: sorted(set(slots)) for gid, slots in by_group.items()}


def count_moved(before: dict, after: dict) -> int:
    moved = 0
    for gid, after_slots in after.items():
        before_slots = before.get(gid, [])
        for i in range(min(len(before_slots), len(after_slots))):
            if before_slots[i] != after_slots[i]:
                moved += 1
        moved += abs(len(before_slots) - len(after_slots))
    return moved


def _solve_and_persist(db, version_id, stability_weight, previous_from_version_id):
    data = build_solver_input(db, previous_from_version_id=previous_from_version_id)
    result = solve(data, weights={"section_gaps": 10, "teacher_gaps": 5, "stability": 15},
                    config=SolveConfig(time_limit_seconds=20, num_workers=4, deterministic=True,
                                        random_seed=7, stability_weight=stability_weight))
    assert result.is_feasible
    persist_solve_result(db, version_id, result, preserve_locks=False)
    return result


def test_stability_reduces_moved_sessions():
    db = make_db()
    v1_id = seed(db)
    data = build_solver_input(db)
    result1 = solve(data, weights={"section_gaps": 10, "teacher_gaps": 5},
                     config=SolveConfig(time_limit_seconds=20, num_workers=4, deterministic=True, random_seed=7))
    assert result1.is_feasible and not result1.unplaced
    persist_solve_result(db, v1_id, result1)
    before = occurrence_slots(db, v1_id)

    # Disruption: the Maths teacher becomes unavailable on day 2 (Wed).
    from app.models.allocation import Allocation
    from app.models.subject import Subject
    maths = db.query(Subject).filter(Subject.code == "MA301").first()
    teacher_id = db.query(Allocation).filter(Allocation.subject_id == maths.id).first().teacher_id
    db.add(TeacherUnavailability(teacher_id=teacher_id, day_index=2, period_index=None))
    db.commit()

    v2a = TimetableVersion(name="No stability", parent_version_id=v1_id)
    v2b = TimetableVersion(name="With stability", parent_version_id=v1_id)
    db.add_all([v2a, v2b])
    db.commit()

    result_no_stability = _solve_and_persist(db, v2a.id, stability_weight=0.0, previous_from_version_id=v1_id)
    after_no_stability = occurrence_slots(db, v2a.id)
    moved_without = count_moved(before, after_no_stability)

    result_with_stability = _solve_and_persist(db, v2b.id, stability_weight=1.0, previous_from_version_id=v1_id)
    after_with_stability = occurrence_slots(db, v2b.id)
    moved_with = count_moved(before, after_with_stability)

    print(f"moved without stability weight: {moved_without}")
    print(f"moved with stability weight:    {moved_with}")
    assert moved_with <= moved_without


if __name__ == "__main__":
    test_stability_reduces_moved_sessions()
    print("OK")
