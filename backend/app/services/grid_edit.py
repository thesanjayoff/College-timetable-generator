"""Manual timetable editing: conflict checking for drag-and-drop moves and simple
swap-slot suggestions. Lightweight (no CP-SAT) -- meant for instant UI feedback."""
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.room import Room
from app.models.structure import TimeStructure
from app.models.timetable import SessionSection, TimetableSession
from app.solver.grid import TimeGrid


@dataclass
class ConflictResult:
    ok: bool
    conflicts: list[dict] = field(default_factory=list)


def _periods(day_index: int, period_index: int, num_periods: int) -> set[tuple[int, int]]:
    return {(day_index, period_index + k) for k in range(num_periods)}


def check_move(
    db: Session, version_id: int, session_id: int, day_index: int, period_index: int,
    teacher_id: int | None = None, room_id: int | None = None,
) -> ConflictResult:
    session = db.get(TimetableSession, session_id)
    if session is None or session.version_id != version_id:
        return ConflictResult(ok=False, conflicts=[{"category": "not_found", "message": "Session not found"}])

    teacher_id = teacher_id if teacher_id is not None else session.teacher_id
    room_id = room_id if room_id is not None else session.room_id
    num_periods = session.num_periods
    target = _periods(day_index, period_index, num_periods)

    sections = [l.section_id for l in db.query(SessionSection).filter(SessionSection.session_id == session.id).all()]

    others = db.query(TimetableSession).filter(
        TimetableSession.version_id == version_id, TimetableSession.id != session.id
    ).all()
    other_sections = {
        o.id: [l.section_id for l in db.query(SessionSection).filter(SessionSection.session_id == o.id).all()]
        for o in others
    }

    conflicts = []
    for o in others:
        o_periods = _periods(o.day_index, o.period_index, o.num_periods)
        if not (o_periods & target):
            continue
        if teacher_id is not None and o.teacher_id == teacher_id:
            conflicts.append({"category": "teacher_conflict", "message": f"Teacher busy with session {o.id}",
                               "session_id": o.id})
        if room_id is not None and o.room_id == room_id:
            conflicts.append({"category": "room_conflict", "message": f"Room busy with session {o.id}",
                               "session_id": o.id})
        if session.sync_group is None or o.sync_group != session.sync_group:
            shared = set(sections) & set(other_sections.get(o.id, []))
            if shared:
                conflicts.append({"category": "section_conflict",
                                   "message": f"Section(s) {sorted(shared)} already busy with session {o.id}",
                                   "session_id": o.id, "section_ids": sorted(shared)})

    if room_id is not None:
        room = db.get(Room, room_id)
        if room is not None:
            # capacity sanity check against the section(s) this session occupies
            from app.models.college import Section
            total = sum((db.get(Section, s).strength or 0) for s in sections if db.get(Section, s))
            if total and room.capacity < total:
                conflicts.append({"category": "room_capacity", "message":
                                   f"Room capacity {room.capacity} is less than required {total}"})

    return ConflictResult(ok=len(conflicts) == 0, conflicts=conflicts)


def apply_move(db: Session, version_id: int, session_id: int, day_index: int, period_index: int,
                teacher_id: int | None = None, room_id: int | None = None) -> TimetableSession:
    session = db.get(TimetableSession, session_id)
    session.day_index = day_index
    session.period_index = period_index
    if teacher_id is not None:
        session.teacher_id = teacher_id
    if room_id is not None:
        session.room_id = room_id
    db.commit()
    db.refresh(session)
    return session


def suggest_slots(db: Session, version_id: int, session_id: int, structure: TimeStructure, limit: int = 3) -> list[dict]:
    session = db.get(TimetableSession, session_id)
    if session is None:
        return []
    grid = TimeGrid(structure)
    suggestions = []
    for d in grid.day_indices:
        for p in grid.valid_block_starts(d, session.num_periods):
            if d == session.day_index and p == session.period_index:
                continue
            result = check_move(db, version_id, session_id, d, p, session.teacher_id, session.room_id)
            if result.ok:
                suggestions.append({"day_index": d, "period_index": p})
            if len(suggestions) >= limit:
                return suggestions
    return suggestions
