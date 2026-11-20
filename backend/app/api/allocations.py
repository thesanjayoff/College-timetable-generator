from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_read_access, require_write_access
from app.core.security import require_department_access
from app.models.allocation import Allocation
from app.models.college import LabBatch, Section
from app.models.room import Room
from app.models.subject import Subject
from app.models.teacher import Teacher
from app.models.user import User

from app.schemas.allocation import AllocationCreate, AllocationOut, AllocationUpdate

router = APIRouter(prefix="/api/allocations", tags=["allocations"])


def _get_allocation_or_404(db: Session, allocation_id: int) -> Allocation:
    allocation = db.get(Allocation, allocation_id)
    if allocation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Allocation not found")
    return allocation


def _check_fks(db: Session, data: dict):
    if "subject_id" in data and data["subject_id"] is not None:
        if db.get(Subject, data["subject_id"]) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    if "section_id" in data and data["section_id"] is not None:
        if db.get(Section, data["section_id"]) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    if data.get("lab_batch_id") is not None:
        if db.get(LabBatch, data["lab_batch_id"]) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LabBatch not found")
    if data.get("teacher_id") is not None:
        if db.get(Teacher, data["teacher_id"]) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found")
    if data.get("room_id") is not None:
        if db.get(Room, data["room_id"]) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")


def _subject_department_id(db: Session, subject_id: int) -> Optional[int]:
    subject = db.get(Subject, subject_id)
    return subject.department_id if subject else None


@router.get("", response_model=list[AllocationOut], dependencies=[Depends(require_read_access)])
def list_allocations(
    section_id: Optional[int] = None,
    subject_id: Optional[int] = None,
    teacher_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Allocation)
    if section_id is not None:
        q = q.filter(Allocation.section_id == section_id)
    if subject_id is not None:
        q = q.filter(Allocation.subject_id == subject_id)
    if teacher_id is not None:
        q = q.filter(Allocation.teacher_id == teacher_id)
    return q.order_by(Allocation.id).all()


@router.get("/{allocation_id}", response_model=AllocationOut, dependencies=[Depends(require_read_access)])
def get_allocation(allocation_id: int, db: Session = Depends(get_db)):
    return _get_allocation_or_404(db, allocation_id)


@router.post("", response_model=AllocationOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_write_access)])
def create_allocation(
    payload: AllocationCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    data = payload.model_dump()
    _check_fks(db, data)
    require_department_access(current_user, _subject_department_id(db, payload.subject_id))
    allocation = Allocation(**data)
    db.add(allocation)
    db.commit()
    db.refresh(allocation)
    return allocation


@router.put("/{allocation_id}", response_model=AllocationOut, dependencies=[Depends(require_write_access)])
def update_allocation(
    allocation_id: int,
    payload: AllocationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    allocation = _get_allocation_or_404(db, allocation_id)
    require_department_access(current_user, _subject_department_id(db, allocation.subject_id))
    data = payload.model_dump(exclude_unset=True)
    _check_fks(db, data)
    if "subject_id" in data and data["subject_id"] is not None:
        require_department_access(current_user, _subject_department_id(db, data["subject_id"]))
    for field, value in data.items():
        setattr(allocation, field, value)
    db.commit()
    db.refresh(allocation)
    return allocation


@router.delete("/{allocation_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_write_access)])
def delete_allocation(
    allocation_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    allocation = _get_allocation_or_404(db, allocation_id)
    require_department_access(current_user, _subject_department_id(db, allocation.subject_id))
    db.delete(allocation)
    db.commit()
    return None
