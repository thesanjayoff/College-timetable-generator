from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_read_access, require_write_access
from app.core.security import require_department_access
from app.services.audit import log_action
from app.models.college import Department
from app.models.subject import Subject
from app.models.teacher import Teacher, TeacherPreference, TeacherSubject, TeacherUnavailability
from app.models.user import User
from app.schemas.teacher import (
    TeacherCreate,
    TeacherOut,
    TeacherPreferenceNestedCreate,
    TeacherPreferenceOut,
    TeacherPreferenceUpdate,
    TeacherSubjectNestedCreate,
    TeacherSubjectOut,
    TeacherUnavailabilityNestedCreate,
    TeacherUnavailabilityOut,
    TeacherUpdate,
)

router = APIRouter(prefix="/api/teachers", tags=["teachers"])


def _get_teacher_or_404(db: Session, teacher_id: int) -> Teacher:
    teacher = db.get(Teacher, teacher_id)
    if teacher is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found")
    return teacher


@router.get("", response_model=list[TeacherOut], dependencies=[Depends(require_read_access)])
def list_teachers(department_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(Teacher)
    if department_id is not None:
        q = q.filter(Teacher.department_id == department_id)
    return q.order_by(Teacher.id).all()


@router.get("/{teacher_id}", response_model=TeacherOut, dependencies=[Depends(require_read_access)])
def get_teacher(teacher_id: int, db: Session = Depends(get_db)):
    return _get_teacher_or_404(db, teacher_id)


@router.post("", response_model=TeacherOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_write_access)])
def create_teacher(
    payload: TeacherCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    if db.get(Department, payload.department_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    require_department_access(current_user, payload.department_id)
    existing = db.query(Teacher).filter(Teacher.code == payload.code).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Teacher code already exists")
    teacher = Teacher(**payload.model_dump())
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    return teacher


@router.put("/{teacher_id}", response_model=TeacherOut, dependencies=[Depends(require_write_access)])
def update_teacher(
    teacher_id: int,
    payload: TeacherUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    teacher = _get_teacher_or_404(db, teacher_id)
    require_department_access(current_user, teacher.department_id)
    data = payload.model_dump(exclude_unset=True)
    if "department_id" in data:
        if db.get(Department, data["department_id"]) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
        require_department_access(current_user, data["department_id"])
    for field, value in data.items():
        setattr(teacher, field, value)
    db.commit()
    db.refresh(teacher)
    return teacher


@router.delete("/{teacher_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_write_access)])
def delete_teacher(
    teacher_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    teacher = _get_teacher_or_404(db, teacher_id)
    require_department_access(current_user, teacher.department_id)
    db.delete(teacher)
    db.commit()
    return None


# ---- Nested teacher-subjects ----

@router.get("/{teacher_id}/subjects", response_model=list[TeacherSubjectOut],
            dependencies=[Depends(require_read_access)])
def list_teacher_subjects(teacher_id: int, db: Session = Depends(get_db)):
    _get_teacher_or_404(db, teacher_id)
    return db.query(TeacherSubject).filter(TeacherSubject.teacher_id == teacher_id).order_by(
        TeacherSubject.id
    ).all()


@router.post("/{teacher_id}/subjects", response_model=TeacherSubjectOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_write_access)])
def add_teacher_subject(
    teacher_id: int,
    payload: TeacherSubjectNestedCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    teacher = _get_teacher_or_404(db, teacher_id)
    require_department_access(current_user, teacher.department_id)
    if db.get(Subject, payload.subject_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    link = TeacherSubject(teacher_id=teacher_id, subject_id=payload.subject_id)
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


@router.delete("/{teacher_id}/subjects/{link_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_write_access)])
def remove_teacher_subject(
    teacher_id: int, link_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    teacher = _get_teacher_or_404(db, teacher_id)
    require_department_access(current_user, teacher.department_id)
    link = db.get(TeacherSubject, link_id)
    if link is None or link.teacher_id != teacher_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TeacherSubject link not found")
    db.delete(link)
    db.commit()
    return None


# ---- Nested unavailability ----

@router.get("/{teacher_id}/unavailability", response_model=list[TeacherUnavailabilityOut],
            dependencies=[Depends(require_read_access)])
def list_teacher_unavailability(teacher_id: int, db: Session = Depends(get_db)):
    _get_teacher_or_404(db, teacher_id)
    return db.query(TeacherUnavailability).filter(
        TeacherUnavailability.teacher_id == teacher_id
    ).order_by(TeacherUnavailability.id).all()


@router.post("/{teacher_id}/unavailability", response_model=TeacherUnavailabilityOut,
             status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_write_access)])
def add_teacher_unavailability(
    teacher_id: int,
    payload: TeacherUnavailabilityNestedCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    teacher = _get_teacher_or_404(db, teacher_id)
    require_department_access(current_user, teacher.department_id)
    row = TeacherUnavailability(teacher_id=teacher_id, **payload.model_dump())
    db.add(row)
    log_action(db, current_user, "create", "teacher_unavailability", teacher_id, payload.model_dump(mode="json"))
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{teacher_id}/unavailability/{row_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_write_access)])
def remove_teacher_unavailability(
    teacher_id: int, row_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    teacher = _get_teacher_or_404(db, teacher_id)
    require_department_access(current_user, teacher.department_id)
    row = db.get(TeacherUnavailability, row_id)
    if row is None or row.teacher_id != teacher_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unavailability entry not found")
    db.delete(row)
    log_action(db, current_user, "delete", "teacher_unavailability", teacher_id,
               {"day_index": row.day_index, "period_index": row.period_index})
    db.commit()
    return None


# ---- Nested preferences ----

@router.get("/{teacher_id}/preferences", response_model=list[TeacherPreferenceOut],
            dependencies=[Depends(require_read_access)])
def list_teacher_preferences(teacher_id: int, db: Session = Depends(get_db)):
    _get_teacher_or_404(db, teacher_id)
    return db.query(TeacherPreference).filter(
        TeacherPreference.teacher_id == teacher_id
    ).order_by(TeacherPreference.id).all()


@router.post("/{teacher_id}/preferences", response_model=TeacherPreferenceOut,
             status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_write_access)])
def add_teacher_preference(
    teacher_id: int,
    payload: TeacherPreferenceNestedCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    teacher = _get_teacher_or_404(db, teacher_id)
    require_department_access(current_user, teacher.department_id)
    row = TeacherPreference(teacher_id=teacher_id, **payload.model_dump())
    db.add(row)
    log_action(db, current_user, "create", "teacher_preference", teacher_id, payload.model_dump(mode="json"))
    db.commit()
    db.refresh(row)
    return row


@router.put("/{teacher_id}/preferences/{row_id}", response_model=TeacherPreferenceOut,
            dependencies=[Depends(require_write_access)])
def update_teacher_preference(
    teacher_id: int,
    row_id: int,
    payload: TeacherPreferenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    teacher = _get_teacher_or_404(db, teacher_id)
    require_department_access(current_user, teacher.department_id)
    row = db.get(TeacherPreference, row_id)
    if row is None or row.teacher_id != teacher_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preference not found")
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(row, field, value)
    log_action(db, current_user, "update", "teacher_preference", teacher_id,
               payload.model_dump(exclude_unset=True, mode="json"))
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{teacher_id}/preferences/{row_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_write_access)])
def remove_teacher_preference(
    teacher_id: int, row_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    teacher = _get_teacher_or_404(db, teacher_id)
    require_department_access(current_user, teacher.department_id)
    row = db.get(TeacherPreference, row_id)
    if row is None or row.teacher_id != teacher_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preference not found")
    db.delete(row)
    log_action(db, current_user, "delete", "teacher_preference", teacher_id,
               {"preference_type": row.preference_type.value})
    db.commit()
    return None
