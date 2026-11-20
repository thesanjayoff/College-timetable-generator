from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import require_read_access
from app.services.substitution import plan_substitutions

router = APIRouter(prefix="/api/versions/{version_id}/substitution", tags=["substitution"])


@router.get("", dependencies=[Depends(require_read_access)])
def get_substitution_plan(version_id: int, teacher_id: int, day_index: int, db: Session = Depends(get_db)):
    return plan_substitutions(db, version_id, teacher_id, day_index)
