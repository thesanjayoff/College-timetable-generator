from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_db, require_read_access, require_write_access
from app.models.structure import PeriodSlot, TimeStructure, WorkingDay
from app.schemas.structure import (
    PeriodSlotNestedCreate,
    PeriodSlotOut,
    PeriodSlotUpdate,
    TimeStructureCreate,
    TimeStructureOut,
    TimeStructureUpdate,
    WorkingDayNestedCreate,
    WorkingDayOut,
    WorkingDayUpdate,
)

router = APIRouter(prefix="/api/time-structures", tags=["time-structures"])


def _get_or_404(db: Session, ts_id: int) -> TimeStructure:
    ts = db.query(TimeStructure).options(
        selectinload(TimeStructure.days), selectinload(TimeStructure.periods)
    ).filter(TimeStructure.id == ts_id).first()
    if ts is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TimeStructure not found")
    return ts


@router.get("", response_model=list[TimeStructureOut], dependencies=[Depends(require_read_access)])
def list_time_structures(db: Session = Depends(get_db)):
    return db.query(TimeStructure).options(
        selectinload(TimeStructure.days), selectinload(TimeStructure.periods)
    ).order_by(TimeStructure.id).all()


@router.get("/{ts_id}", response_model=TimeStructureOut, dependencies=[Depends(require_read_access)])
def get_time_structure(ts_id: int, db: Session = Depends(get_db)):
    return _get_or_404(db, ts_id)


@router.post("", response_model=TimeStructureOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_write_access)])
def create_time_structure(payload: TimeStructureCreate, db: Session = Depends(get_db)):
    ts = TimeStructure(name=payload.name, is_default=payload.is_default)
    for day in payload.days:
        ts.days.append(WorkingDay(**day.model_dump()))
    for period in payload.periods:
        ts.periods.append(PeriodSlot(**period.model_dump()))
    db.add(ts)
    db.commit()
    db.refresh(ts)
    return ts


@router.put("/{ts_id}", response_model=TimeStructureOut, dependencies=[Depends(require_write_access)])
def update_time_structure(ts_id: int, payload: TimeStructureUpdate, db: Session = Depends(get_db)):
    ts = _get_or_404(db, ts_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(ts, field, value)
    db.commit()
    db.refresh(ts)
    return ts


@router.delete("/{ts_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_write_access)])
def delete_time_structure(ts_id: int, db: Session = Depends(get_db)):
    ts = _get_or_404(db, ts_id)
    db.delete(ts)
    db.commit()
    return None


# ---- Nested working days ----

@router.get("/{ts_id}/days", response_model=list[WorkingDayOut], dependencies=[Depends(require_read_access)])
def list_working_days(ts_id: int, db: Session = Depends(get_db)):
    _get_or_404(db, ts_id)
    return db.query(WorkingDay).filter(WorkingDay.time_structure_id == ts_id).order_by(WorkingDay.day_index).all()


@router.post("/{ts_id}/days", response_model=WorkingDayOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_write_access)])
def create_working_day(ts_id: int, payload: WorkingDayNestedCreate, db: Session = Depends(get_db)):
    _get_or_404(db, ts_id)
    day = WorkingDay(time_structure_id=ts_id, **payload.model_dump())
    db.add(day)
    db.commit()
    db.refresh(day)
    return day


@router.put("/{ts_id}/days/{day_id}", response_model=WorkingDayOut, dependencies=[Depends(require_write_access)])
def update_working_day(ts_id: int, day_id: int, payload: WorkingDayUpdate, db: Session = Depends(get_db)):
    _get_or_404(db, ts_id)
    day = db.get(WorkingDay, day_id)
    if day is None or day.time_structure_id != ts_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WorkingDay not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(day, field, value)
    db.commit()
    db.refresh(day)
    return day


@router.delete("/{ts_id}/days/{day_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_write_access)])
def delete_working_day(ts_id: int, day_id: int, db: Session = Depends(get_db)):
    _get_or_404(db, ts_id)
    day = db.get(WorkingDay, day_id)
    if day is None or day.time_structure_id != ts_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WorkingDay not found")
    db.delete(day)
    db.commit()
    return None


# ---- Nested period slots ----

@router.get("/{ts_id}/periods", response_model=list[PeriodSlotOut], dependencies=[Depends(require_read_access)])
def list_period_slots(ts_id: int, db: Session = Depends(get_db)):
    _get_or_404(db, ts_id)
    return db.query(PeriodSlot).filter(PeriodSlot.time_structure_id == ts_id).order_by(PeriodSlot.period_index).all()


@router.post("/{ts_id}/periods", response_model=PeriodSlotOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_write_access)])
def create_period_slot(ts_id: int, payload: PeriodSlotNestedCreate, db: Session = Depends(get_db)):
    _get_or_404(db, ts_id)
    period = PeriodSlot(time_structure_id=ts_id, **payload.model_dump())
    db.add(period)
    db.commit()
    db.refresh(period)
    return period


@router.put("/{ts_id}/periods/{period_id}", response_model=PeriodSlotOut,
            dependencies=[Depends(require_write_access)])
def update_period_slot(ts_id: int, period_id: int, payload: PeriodSlotUpdate, db: Session = Depends(get_db)):
    _get_or_404(db, ts_id)
    period = db.get(PeriodSlot, period_id)
    if period is None or period.time_structure_id != ts_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PeriodSlot not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(period, field, value)
    db.commit()
    db.refresh(period)
    return period


@router.delete("/{ts_id}/periods/{period_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_write_access)])
def delete_period_slot(ts_id: int, period_id: int, db: Session = Depends(get_db)):
    _get_or_404(db, ts_id)
    period = db.get(PeriodSlot, period_id)
    if period is None or period.time_structure_id != ts_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PeriodSlot not found")
    db.delete(period)
    db.commit()
    return None
