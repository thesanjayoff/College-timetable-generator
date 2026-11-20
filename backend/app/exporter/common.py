"""Shared helpers for building export data: resolves sessions + period/day labels for a
given version and a view (section/teacher/room)."""
from sqlalchemy.orm import Session

from app.models.structure import PeriodSlot, TimeStructure, WorkingDay
from app.models.timetable import SessionSection, TimetableSession

DAY_NAMES_FALLBACK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def get_default_structure(db: Session) -> TimeStructure:
    s = db.query(TimeStructure).filter(TimeStructure.is_default.is_(True)).first()
    return s or db.query(TimeStructure).first()


def structure_grid_labels(structure: TimeStructure) -> tuple[list[WorkingDay], list[PeriodSlot]]:
    days = sorted(structure.days, key=lambda d: d.day_index)
    periods = sorted(structure.periods, key=lambda p: p.period_index)
    return days, periods


def sessions_for_view(db: Session, version_id: int, section_id: int | None = None,
                       teacher_id: int | None = None, room_id: int | None = None) -> list[TimetableSession]:
    q = db.query(TimetableSession).filter(TimetableSession.version_id == version_id)
    if teacher_id is not None:
        q = q.filter(TimetableSession.teacher_id == teacher_id)
    if room_id is not None:
        q = q.filter(TimetableSession.room_id == room_id)
    rows = q.all()
    if section_id is None:
        return rows
    ids = [r.id for r in rows]
    if not ids:
        return []
    linked = {l.session_id for l in db.query(SessionSection).filter(
        SessionSection.session_id.in_(ids), SessionSection.section_id == section_id
    ).all()}
    return [r for r in rows if r.id in linked]


def cell_label(session: TimetableSession) -> str:
    subject = session.subject.code if session.subject else "?"
    teacher = session.teacher.code if session.teacher else ""
    room = session.room.code if session.room else ""
    batch = f" ({session.lab_batch.name})" if session.lab_batch_id and session.lab_batch else ""
    parts = [p for p in [subject + batch, teacher, room] if p]
    return "\n".join(parts)
