from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.enums import VersionStatus
from app.models.timetable import SessionSection, TimetableSession, TimetableVersion, UnplacedRequirement
from app.models.weight import DEFAULT_WEIGHTS
from app.services.grid_edit import apply_move, check_move, suggest_slots
from app.models.structure import TimeStructure
from app.verifier.verify import verify_version

router = APIRouter(prefix="/api/versions", tags=["versions"])


class VersionCreate(BaseModel):
    name: str
    parent_version_id: int | None = None
    notes: str | None = None


class VersionOut(BaseModel):
    id: int
    name: str
    status: str
    parent_version_id: int | None
    hard_violations: int
    soft_score: float
    solve_status: str | None
    created_at: datetime

    class Config:
        from_attributes = True


def _version_or_404(db: Session, version_id: int) -> TimetableVersion:
    v = db.get(TimetableVersion, version_id)
    if v is None:
        raise HTTPException(404, "Version not found")
    return v


@router.get("")
def list_versions(db: Session = Depends(get_db)):
    rows = db.query(TimetableVersion).order_by(TimetableVersion.created_at.desc()).all()
    return [
        {"id": r.id, "name": r.name, "status": r.status.value, "parent_version_id": r.parent_version_id,
         "hard_violations": r.hard_violations, "soft_score": r.soft_score, "solve_status": r.solve_status,
         "created_at": r.created_at}
        for r in rows
    ]


@router.post("")
def create_version(payload: VersionCreate, db: Session = Depends(get_db)):
    v = TimetableVersion(name=payload.name, parent_version_id=payload.parent_version_id, notes=payload.notes)
    db.add(v)
    db.commit()
    db.refresh(v)
    if payload.parent_version_id:
        parent_sessions = db.query(TimetableSession).filter(
            TimetableSession.version_id == payload.parent_version_id
        ).all()
        for s in parent_sessions:
            links = [l.section_id for l in db.query(SessionSection).filter(SessionSection.session_id == s.id).all()]
            new_row = TimetableSession(
                version_id=v.id, session_kind=s.session_kind, day_index=s.day_index, period_index=s.period_index,
                num_periods=s.num_periods, subject_id=s.subject_id, teacher_id=s.teacher_id, room_id=s.room_id,
                lab_batch_id=s.lab_batch_id, allocation_id=s.allocation_id, elective_basket_id=s.elective_basket_id,
                elective_option_id=s.elective_option_id, combined_class_id=s.combined_class_id,
                sync_group=s.sync_group, is_locked=s.is_locked,
            )
            db.add(new_row)
            db.flush()
            for sec in links:
                db.add(SessionSection(session_id=new_row.id, section_id=sec))
        db.commit()
    return {"id": v.id}


@router.get("/{version_id}")
def get_version(version_id: int, db: Session = Depends(get_db)):
    v = _version_or_404(db, version_id)
    return {
        "id": v.id, "name": v.name, "status": v.status.value, "parent_version_id": v.parent_version_id,
        "hard_violations": v.hard_violations, "soft_score": v.soft_score, "solve_status": v.solve_status,
        "scorecard": v.scorecard, "notes": v.notes, "created_at": v.created_at,
    }


@router.delete("/{version_id}")
def delete_version(version_id: int, db: Session = Depends(get_db)):
    v = _version_or_404(db, version_id)
    if v.status == VersionStatus.PUBLISHED:
        raise HTTPException(400, "Cannot delete a published version")
    db.delete(v)
    db.commit()
    return {"ok": True}


@router.get("/{version_id}/sessions")
def list_sessions(version_id: int, section_id: int | None = None, teacher_id: int | None = None,
                   room_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(TimetableSession).filter(TimetableSession.version_id == version_id)
    if teacher_id is not None:
        q = q.filter(TimetableSession.teacher_id == teacher_id)
    if room_id is not None:
        q = q.filter(TimetableSession.room_id == room_id)
    rows = q.all()
    ids = [r.id for r in rows]
    links = db.query(SessionSection).filter(SessionSection.session_id.in_(ids)).all() if ids else []
    section_map: dict[int, list[int]] = {}
    for l in links:
        section_map.setdefault(l.session_id, []).append(l.section_id)

    out = []
    for r in rows:
        secs = section_map.get(r.id, [])
        if section_id is not None and section_id not in secs:
            continue
        out.append({
            "id": r.id, "kind": r.session_kind.value, "day_index": r.day_index, "period_index": r.period_index,
            "num_periods": r.num_periods, "subject_id": r.subject_id,
            "subject_code": r.subject.code if r.subject else None,
            "teacher_id": r.teacher_id, "teacher_name": r.teacher.name if r.teacher else None,
            "room_id": r.room_id, "room_code": r.room.code if r.room else None,
            "lab_batch_id": r.lab_batch_id, "section_ids": secs, "sync_group": r.sync_group,
            "is_locked": r.is_locked, "elective_basket_id": r.elective_basket_id,
            "combined_class_id": r.combined_class_id,
        })
    return out


@router.get("/{version_id}/unplaced")
def list_unplaced(version_id: int, db: Session = Depends(get_db)):
    rows = db.query(UnplacedRequirement).filter(UnplacedRequirement.version_id == version_id).all()
    return [
        {"id": r.id, "description": r.description, "allocation_id": r.allocation_id,
         "elective_basket_id": r.elective_basket_id, "combined_class_id": r.combined_class_id,
         "sessions_missing": r.sessions_missing}
        for r in rows
    ]


@router.post("/{version_id}/verify")
def verify(version_id: int, db: Session = Depends(get_db)):
    _version_or_404(db, version_id)
    report = verify_version(db, version_id, DEFAULT_WEIGHTS)
    v = db.get(TimetableVersion, version_id)
    v.hard_violations = len(report.hard_violations)
    v.soft_score = report.scorecard.get("total_soft_score", 0)
    v.scorecard = report.scorecard
    db.commit()
    return report.to_dict()


@router.post("/{version_id}/publish")
def publish(version_id: int, db: Session = Depends(get_db)):
    v = _version_or_404(db, version_id)
    report = verify_version(db, version_id, DEFAULT_WEIGHTS)
    if not report.is_clean:
        raise HTTPException(409, {"message": "Cannot publish: hard violations remain",
                                   "violations": [vi.message for vi in report.hard_violations]})
    v.status = VersionStatus.PUBLISHED
    v.published_at = datetime.now(timezone.utc)
    v.hard_violations = 0
    v.soft_score = report.scorecard.get("total_soft_score", 0)
    v.scorecard = report.scorecard
    db.commit()
    return {"ok": True}


@router.post("/{version_id}/rollback")
def rollback(version_id: int, db: Session = Depends(get_db)):
    v = _version_or_404(db, version_id)
    v.status = VersionStatus.DRAFT
    db.commit()
    return {"ok": True}


class MoveRequest(BaseModel):
    day_index: int
    period_index: int
    teacher_id: int | None = None
    room_id: int | None = None
    confirm: bool = False


@router.post("/{version_id}/sessions/{session_id}/check-move")
def check_session_move(version_id: int, session_id: int, payload: MoveRequest, db: Session = Depends(get_db)):
    result = check_move(db, version_id, session_id, payload.day_index, payload.period_index,
                         payload.teacher_id, payload.room_id)
    return {"ok": result.ok, "conflicts": result.conflicts}


@router.post("/{version_id}/sessions/{session_id}/move")
def move_session(version_id: int, session_id: int, payload: MoveRequest, db: Session = Depends(get_db)):
    session = db.get(TimetableSession, session_id)
    if session is None or session.version_id != version_id:
        raise HTTPException(404, "Session not found")
    if session.is_locked:
        raise HTTPException(409, "Session is locked")
    result = check_move(db, version_id, session_id, payload.day_index, payload.period_index,
                         payload.teacher_id, payload.room_id)
    if not result.ok and not payload.confirm:
        raise HTTPException(409, {"message": "Move would break hard constraints", "conflicts": result.conflicts})
    updated = apply_move(db, version_id, session_id, payload.day_index, payload.period_index,
                          payload.teacher_id, payload.room_id)
    report = verify_version(db, version_id, DEFAULT_WEIGHTS)
    v = db.get(TimetableVersion, version_id)
    v.hard_violations = len(report.hard_violations)
    v.soft_score = report.scorecard.get("total_soft_score", 0)
    v.scorecard = report.scorecard
    db.commit()
    return {"ok": True, "session_id": updated.id, "verification": report.to_dict()}


@router.get("/{version_id}/sessions/{session_id}/suggestions")
def suggestions(version_id: int, session_id: int, db: Session = Depends(get_db)):
    session = db.get(TimetableSession, session_id)
    if session is None:
        raise HTTPException(404, "Session not found")
    section_link = db.query(SessionSection).filter(SessionSection.session_id == session_id).first()
    structure = None
    if section_link and section_link.section and section_link.section.program:
        structure_id = (section_link.section.time_structure_id
                         or section_link.section.program.time_structure_id)
    else:
        structure_id = None
    structure = db.get(TimeStructure, structure_id) if structure_id else db.query(TimeStructure).filter(
        TimeStructure.is_default.is_(True)).first()
    if structure is None:
        return []
    return suggest_slots(db, version_id, session_id, structure)


@router.post("/{version_id}/sessions/{session_id}/lock")
def lock_session(version_id: int, session_id: int, db: Session = Depends(get_db)):
    session = db.get(TimetableSession, session_id)
    if session is None or session.version_id != version_id:
        raise HTTPException(404, "Session not found")
    session.is_locked = True
    db.commit()
    return {"ok": True}


@router.post("/{version_id}/sessions/{session_id}/unlock")
def unlock_session(version_id: int, session_id: int, db: Session = Depends(get_db)):
    session = db.get(TimetableSession, session_id)
    if session is None or session.version_id != version_id:
        raise HTTPException(404, "Session not found")
    session.is_locked = False
    db.commit()
    return {"ok": True}


@router.get("/{version_id}/diff/{other_version_id}")
def diff_versions(version_id: int, other_version_id: int, db: Session = Depends(get_db)):
    def snapshot(vid):
        rows = db.query(TimetableSession).filter(TimetableSession.version_id == vid).all()
        by_key = {}
        for r in rows:
            key = (r.subject_id, r.teacher_id, r.lab_batch_id, r.combined_class_id, r.elective_option_id)
            by_key[key] = (r.day_index, r.period_index, r.room_id)
        return by_key

    a, b = snapshot(version_id), snapshot(other_version_id)
    moved, added, removed, unchanged = [], [], [], 0
    for k, va in a.items():
        if k not in b:
            removed.append({"key": k, "was": va})
        elif b[k] != va:
            moved.append({"key": k, "from": va, "to": b[k]})
        else:
            unchanged += 1
    for k, vb in b.items():
        if k not in a:
            added.append({"key": k, "now": vb})
    return {"moved": moved, "added": added, "removed": removed, "unchanged": unchanged}
