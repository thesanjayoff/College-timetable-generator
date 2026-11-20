"""Unauthenticated, read-only endpoints for sharing a published timetable with students
and staff via a link (no login, no write access, nothing beyond what the link's owner
explicitly chose to share). Never add anything here that requires a token dependency --
that belongs in the normal authenticated routers."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.timetable import SessionSection, TimetableSession, TimetableVersion

router = APIRouter(prefix="/api/public", tags=["public"])


def _version_by_token_or_404(db: Session, token: str) -> TimetableVersion:
    v = db.query(TimetableVersion).filter(TimetableVersion.share_token == token).first()
    if v is None:
        raise HTTPException(404, "Share link not found or revoked")
    return v


@router.get("/share/{token}")
def get_shared_version(token: str, db: Session = Depends(get_db)):
    v = _version_by_token_or_404(db, token)
    return {
        "id": v.id, "name": v.name, "status": v.status.value,
        "published_at": v.published_at, "hard_violations": v.hard_violations,
    }


@router.get("/share/{token}/sessions")
def get_shared_sessions(token: str, section_id: int | None = None, teacher_id: int | None = None,
                         room_id: int | None = None, db: Session = Depends(get_db)):
    v = _version_by_token_or_404(db, token)
    q = db.query(TimetableSession).filter(TimetableSession.version_id == v.id)
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
            "num_periods": r.num_periods, "subject_code": r.subject.code if r.subject else None,
            "teacher_name": r.teacher.name if r.teacher else None, "room_code": r.room.code if r.room else None,
            "section_ids": secs,
        })
    return out
