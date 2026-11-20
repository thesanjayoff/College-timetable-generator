from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_read_access, require_write_access
from app.core.security import require_department_access
from app.models.college import Department
from app.models.subject import Subject
from app.models.user import User
from app.schemas.subject import SubjectCreate, SubjectOut, SubjectUpdate

router = APIRouter(prefix="/api/subjects", tags=["subjects"])


@router.get("", response_model=list[SubjectOut], dependencies=[Depends(require_read_access)])
def list_subjects(department_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(Subject)
    if department_id is not None:
        q = q.filter(Subject.department_id == department_id)
    return q.order_by(Subject.id).all()


@router.get("/{subject_id}", response_model=SubjectOut, dependencies=[Depends(require_read_access)])
def get_subject(subject_id: int, db: Session = Depends(get_db)):
    subject = db.get(Subject, subject_id)
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    return subject


@router.post("", response_model=SubjectOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_write_access)])
def create_subject(
    payload: SubjectCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    if db.get(Department, payload.department_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    require_department_access(current_user, payload.department_id)
    existing = db.query(Subject).filter(Subject.code == payload.code).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subject code already exists")
    subject = Subject(**payload.model_dump())
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject


@router.put("/{subject_id}", response_model=SubjectOut, dependencies=[Depends(require_write_access)])
def update_subject(
    subject_id: int,
    payload: SubjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    subject = db.get(Subject, subject_id)
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    require_department_access(current_user, subject.department_id)
    data = payload.model_dump(exclude_unset=True)
    if "department_id" in data:
        if db.get(Department, data["department_id"]) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
        require_department_access(current_user, data["department_id"])
    for field, value in data.items():
        setattr(subject, field, value)
    db.commit()
    db.refresh(subject)
    return subject


@router.delete("/{subject_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_write_access)])
def delete_subject(
    subject_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    subject = db.get(Subject, subject_id)
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    require_department_access(current_user, subject.department_id)
    db.delete(subject)
    db.commit()
    return None
