"""Substitution planner: for an absent teacher on a given day, suggest eligible, free
replacement teachers ranked by current workload (lightest first)."""
from sqlalchemy.orm import Session

from app.models.teacher import Teacher, TeacherSubject, TeacherUnavailability
from app.models.timetable import TimetableSession


def _teacher_weekly_load(db: Session, version_id: int, teacher_id: int) -> int:
    rows = db.query(TimetableSession).filter(
        TimetableSession.version_id == version_id, TimetableSession.teacher_id == teacher_id
    ).all()
    return sum(r.num_periods for r in rows)


def _is_free(db: Session, version_id: int, teacher_id: int, day_index: int, period_index: int,
             num_periods: int) -> bool:
    target = {period_index + k for k in range(num_periods)}
    rows = db.query(TimetableSession).filter(
        TimetableSession.version_id == version_id, TimetableSession.teacher_id == teacher_id,
        TimetableSession.day_index == day_index,
    ).all()
    for r in rows:
        occupied = {r.period_index + k for k in range(r.num_periods)}
        if occupied & target:
            return False
    unavailable = db.query(TeacherUnavailability).filter(TeacherUnavailability.teacher_id == teacher_id).all()
    for u in unavailable:
        if u.day_index != day_index:
            continue
        if u.period_index is None:
            return False
        if u.period_index in target:
            return False
    return True


def plan_substitutions(db: Session, version_id: int, absent_teacher_id: int, day_index: int) -> list[dict]:
    sessions = db.query(TimetableSession).filter(
        TimetableSession.version_id == version_id, TimetableSession.teacher_id == absent_teacher_id,
        TimetableSession.day_index == day_index,
    ).all()

    out = []
    for s in sessions:
        eligible_ids = [
            r.teacher_id for r in db.query(TeacherSubject).filter(TeacherSubject.subject_id == s.subject_id).all()
            if r.teacher_id != absent_teacher_id
        ]
        candidates = []
        for tid in set(eligible_ids):
            if not _is_free(db, version_id, tid, day_index, s.period_index, s.num_periods):
                continue
            teacher = db.get(Teacher, tid)
            candidates.append({
                "teacher_id": tid, "name": teacher.name if teacher else str(tid),
                "current_weekly_load": _teacher_weekly_load(db, version_id, tid),
            })
        candidates.sort(key=lambda c: c["current_weekly_load"])
        out.append({
            "session_id": s.id, "subject_id": s.subject_id, "day_index": s.day_index,
            "period_index": s.period_index, "num_periods": s.num_periods,
            "candidates": candidates,
        })
    return out
