from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_read_access, require_write_access
from app.models.weight import PRESETS, WeightProfile
from app.schemas.weight import WeightProfileCreate, WeightProfileOut, WeightProfileUpdate

router = APIRouter(prefix="/api/weight-profiles", tags=["weight-profiles"])


def _seed_presets_if_empty(db: Session) -> None:
    if db.query(WeightProfile).first() is not None:
        return
    for name, weights in PRESETS.items():
        db.add(WeightProfile(name=name, is_preset=True, weights=weights))
    db.commit()


def _get_or_404(db: Session, profile_id: int) -> WeightProfile:
    profile = db.get(WeightProfile, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WeightProfile not found")
    return profile


@router.get("", response_model=list[WeightProfileOut], dependencies=[Depends(require_read_access)])
def list_weight_profiles(db: Session = Depends(get_db)):
    _seed_presets_if_empty(db)
    return db.query(WeightProfile).order_by(WeightProfile.id).all()


@router.get("/{profile_id}", response_model=WeightProfileOut, dependencies=[Depends(require_read_access)])
def get_weight_profile(profile_id: int, db: Session = Depends(get_db)):
    return _get_or_404(db, profile_id)


@router.post("", response_model=WeightProfileOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_write_access)])
def create_weight_profile(payload: WeightProfileCreate, db: Session = Depends(get_db)):
    existing = db.query(WeightProfile).filter(WeightProfile.name == payload.name).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="WeightProfile name already exists")
    profile = WeightProfile(**payload.model_dump())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.put("/{profile_id}", response_model=WeightProfileOut, dependencies=[Depends(require_write_access)])
def update_weight_profile(profile_id: int, payload: WeightProfileUpdate, db: Session = Depends(get_db)):
    profile = _get_or_404(db, profile_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return profile


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_write_access)])
def delete_weight_profile(profile_id: int, db: Session = Depends(get_db)):
    profile = _get_or_404(db, profile_id)
    if profile.is_preset:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete a preset weight profile")
    db.delete(profile)
    db.commit()
    return None
