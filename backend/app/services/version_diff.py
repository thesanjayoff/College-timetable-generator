"""Occurrence-aware diff between two timetable versions. A naive diff keyed only by
(subject, teacher, ...) collides whenever the same subject/teacher pair meets more than
once a week, which is the common case, not an edge case -- so this matches occurrences
of the same requirement group by sorted (day, period) order, the same approach the
solver's own stability/lock matching already uses (app.solver.builder._group_id_for_session),
rather than re-deriving a second, inconsistent notion of "the same occurrence"."""
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.timetable import SessionSection, TimetableSession
from app.solver.builder import _group_id_for_session


@dataclass
class OccurrenceDiff:
    group_id: str
    occurrence: int
    before: dict | None  # {session_id, day_index, period_index, room_id, teacher_id, section_ids}
    after: dict | None


def _grouped(db: Session, version_id: int) -> dict[str, list[dict]]:
    rows = db.query(TimetableSession).filter(TimetableSession.version_id == version_id).all()
    ids = [r.id for r in rows]
    links = db.query(SessionSection).filter(SessionSection.session_id.in_(ids)).all() if ids else []
    sections_by_session: dict[int, list[int]] = {}
    for l in links:
        sections_by_session.setdefault(l.session_id, []).append(l.section_id)

    by_group: dict[str, list[dict]] = {}
    for r in rows:
        gid = _group_id_for_session(r)
        if not gid:
            continue
        by_group.setdefault(gid, []).append({
            "session_id": r.id, "day_index": r.day_index, "period_index": r.period_index,
            "room_id": r.room_id, "teacher_id": r.teacher_id,
            "section_ids": sections_by_session.get(r.id, []),
        })
    for gid in by_group:
        by_group[gid].sort(key=lambda s: (s["day_index"], s["period_index"]))
    return by_group


def diff_versions_by_occurrence(db: Session, version_a_id: int, version_b_id: int,
                                 unchanged_count: list[int] | None = None) -> list[OccurrenceDiff]:
    """Returns one entry per occurrence slot that changed (moved/added/removed) between
    the two versions, matched by sorted position within its requirement group -- not by
    (subject, teacher, ...) alone, which would collide across a group's own repeated
    weekly occurrences. If `unchanged_count` is passed, its single element is set to the
    number of occurrence slots that matched exactly."""
    before = _grouped(db, version_a_id)
    after = _grouped(db, version_b_id)
    out: list[OccurrenceDiff] = []
    unchanged = 0
    for gid in set(before) | set(after):
        b_list, a_list = before.get(gid, []), after.get(gid, [])
        for i in range(max(len(b_list), len(a_list))):
            b = b_list[i] if i < len(b_list) else None
            a = a_list[i] if i < len(a_list) else None
            if b and a and (b["day_index"], b["period_index"], b["room_id"]) == \
                    (a["day_index"], a["period_index"], a["room_id"]):
                unchanged += 1
                continue
            out.append(OccurrenceDiff(group_id=gid, occurrence=i, before=b, after=a))
    if unchanged_count is not None:
        unchanged_count.append(unchanged)
    return out
