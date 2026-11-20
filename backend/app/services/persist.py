"""Writes a solver SolveResult into the database as TimetableSession rows."""
from sqlalchemy.orm import Session

from app.models.allocation import Allocation
from app.models.enums import SessionKind
from app.models.timetable import SessionSection, TimetableSession, UnplacedRequirement
from app.solver.service import SolveResult

_KIND_MAP = {
    "regular": SessionKind.REGULAR,
    "lab": SessionKind.REGULAR,
    "combined": SessionKind.COMBINED,
    "elective": SessionKind.ELECTIVE,
}


def clear_version_sessions(db: Session, version_id: int) -> None:
    session_ids = [r.id for r in db.query(TimetableSession.id).filter(TimetableSession.version_id == version_id).all()]
    if session_ids:
        db.query(SessionSection).filter(SessionSection.session_id.in_(session_ids)).delete(synchronize_session=False)
    db.query(TimetableSession).filter(TimetableSession.version_id == version_id).delete(synchronize_session=False)
    db.query(UnplacedRequirement).filter(UnplacedRequirement.version_id == version_id).delete(synchronize_session=False)


def persist_solve_result(db: Session, version_id: int, result: SolveResult, preserve_locks: bool = True) -> None:
    if preserve_locks:
        locked_rows = db.query(TimetableSession).filter(
            TimetableSession.version_id == version_id, TimetableSession.is_locked.is_(True)
        ).all()
        locked_ids = {r.id for r in locked_rows}
        db.query(SessionSection).filter(
            SessionSection.session_id.in_(
                [r.id for r in db.query(TimetableSession.id)
                 .filter(TimetableSession.version_id == version_id,
                         TimetableSession.is_locked.is_(False)).all()]
            )
        ).delete(synchronize_session=False)
        db.query(TimetableSession).filter(
            TimetableSession.version_id == version_id, TimetableSession.is_locked.is_(False)
        ).delete(synchronize_session=False)
    else:
        clear_version_sessions(db, version_id)

    db.query(UnplacedRequirement).filter(UnplacedRequirement.version_id == version_id).delete(synchronize_session=False)

    for sess in result.sessions:
        kind = _KIND_MAP[sess.kind]
        sync_group = f"{sess.group_id}_{sess.occurrence}" if len(sess.parts) > 1 else None

        allocation_lookup = {}
        if sess.source_ref.get("type") == "allocation":
            alloc_ids = sess.source_ref.get("allocation_ids", [])
            rows = db.query(Allocation).filter(Allocation.id.in_(alloc_ids)).all()
            allocation_lookup = {r.lab_batch_id: r.id for r in rows}

        for part in sess.parts:
            allocation_id = allocation_lookup.get(part.lab_batch_id) if allocation_lookup else None
            elective_basket_id = None
            elective_option_id = None
            combined_class_id = None
            if sess.source_ref.get("type") == "elective":
                elective_basket_id = sess.source_ref.get("basket_id")
                if part.part_key.startswith("opt_"):
                    elective_option_id = int(part.part_key.split("_", 1)[1])
            elif sess.source_ref.get("type") == "combined":
                combined_class_id = sess.source_ref.get("combined_class_id")

            row = TimetableSession(
                version_id=version_id, session_kind=kind, day_index=sess.day_index,
                period_index=sess.period_index, num_periods=sess.num_periods,
                subject_id=part.subject_id, teacher_id=part.teacher_id, room_id=part.room_id,
                lab_batch_id=part.lab_batch_id, allocation_id=allocation_id,
                elective_basket_id=elective_basket_id, elective_option_id=elective_option_id,
                combined_class_id=combined_class_id, sync_group=sync_group, is_locked=False,
            )
            db.add(row)
            db.flush()
            for sec_id in sess.occupied_section_ids:
                db.add(SessionSection(session_id=row.id, section_id=sec_id))

    for u in result.unplaced:
        db.add(UnplacedRequirement(
            version_id=version_id, description=u.label,
            allocation_id=None, elective_basket_id=u.source_ref.get("basket_id"),
            combined_class_id=u.source_ref.get("combined_class_id"), sessions_missing=1,
        ))

    db.commit()
