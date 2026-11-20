from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_read_access, require_write_access
from app.models.college import Section
from app.models.combined import CombinedClass, CombinedClassSection
from app.models.subject import Subject
from app.models.teacher import Teacher
from app.schemas.combined import (
    CombinedClassCreate,
    CombinedClassOut,
    CombinedClassSectionNestedCreate,
    CombinedClassSectionOut,
    CombinedClassUpdate,
)

router = APIRouter(prefix="/api/combined-classes", tags=["combined-classes"])


def _get_or_404(db: Session, combined_class_id: int) -> CombinedClass:
    cc = db.get(CombinedClass, combined_class_id)
    if cc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CombinedClass not found")
    return cc


def _check_fks(db: Session, data: dict):
    if data.get("subject_id") is not None and db.get(Subject, data["subject_id"]) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    if data.get("teacher_id") is not None and db.get(Teacher, data["teacher_id"]) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found")


@router.get("", response_model=list[CombinedClassOut], dependencies=[Depends(require_read_access)])
def list_combined_classes(db: Session = Depends(get_db)):
    return db.query(CombinedClass).order_by(CombinedClass.id).all()


@router.get("/{combined_class_id}", response_model=CombinedClassOut, dependencies=[Depends(require_read_access)])
def get_combined_class(combined_class_id: int, db: Session = Depends(get_db)):
    return _get_or_404(db, combined_class_id)


@router.post("", response_model=CombinedClassOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_write_access)])
def create_combined_class(payload: CombinedClassCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    _check_fks(db, data)
    cc = CombinedClass(**data)
    db.add(cc)
    db.commit()
    db.refresh(cc)
    return cc


@router.put("/{combined_class_id}", response_model=CombinedClassOut, dependencies=[Depends(require_write_access)])
def update_combined_class(combined_class_id: int, payload: CombinedClassUpdate, db: Session = Depends(get_db)):
    cc = _get_or_404(db, combined_class_id)
    data = payload.model_dump(exclude_unset=True)
    _check_fks(db, data)
    for field, value in data.items():
        setattr(cc, field, value)
    db.commit()
    db.refresh(cc)
    return cc


@router.delete("/{combined_class_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_write_access)])
def delete_combined_class(combined_class_id: int, db: Session = Depends(get_db)):
    cc = _get_or_404(db, combined_class_id)
    db.delete(cc)
    db.commit()
    return None


# ---- Nested sections ----

@router.get("/{combined_class_id}/sections", response_model=list[CombinedClassSectionOut],
            dependencies=[Depends(require_read_access)])
def list_combined_class_sections(combined_class_id: int, db: Session = Depends(get_db)):
    _get_or_404(db, combined_class_id)
    return db.query(CombinedClassSection).filter(
        CombinedClassSection.combined_class_id == combined_class_id
    ).order_by(CombinedClassSection.id).all()


@router.post("/{combined_class_id}/sections", response_model=CombinedClassSectionOut,
             status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_write_access)])
def add_combined_class_section(
    combined_class_id: int, payload: CombinedClassSectionNestedCreate, db: Session = Depends(get_db)
):
    _get_or_404(db, combined_class_id)
    if db.get(Section, payload.section_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    link = CombinedClassSection(combined_class_id=combined_class_id, section_id=payload.section_id)
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


@router.delete("/{combined_class_id}/sections/{link_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_write_access)])
def remove_combined_class_section(combined_class_id: int, link_id: int, db: Session = Depends(get_db)):
    _get_or_404(db, combined_class_id)
    link = db.get(CombinedClassSection, link_id)
    if link is None or link.combined_class_id != combined_class_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CombinedClassSection link not found")
    db.delete(link)
    db.commit()
    return None
