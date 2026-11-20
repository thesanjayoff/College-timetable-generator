from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_read_access, require_write_access
from app.models.college import LabBatch, Program, Section
from app.models.structure import TimeStructure
from app.schemas.college import (
    LabBatchCreate,
    LabBatchNestedCreate,
    LabBatchOut,
    LabBatchUpdate,
    SectionCreate,
    SectionOut,
    SectionUpdate,
)

router = APIRouter(prefix="/api/sections", tags=["sections"])


def _check_fks(db: Session, program_id: Optional[int] = None, time_structure_id: Optional[int] = None):
    if program_id is not None and db.get(Program, program_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")
    if time_structure_id is not None and db.get(TimeStructure, time_structure_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TimeStructure not found")


def _get_section_or_404(db: Session, section_id: int) -> Section:
    section = db.get(Section, section_id)
    if section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    return section


@router.get("", response_model=list[SectionOut], dependencies=[Depends(require_read_access)])
def list_sections(program_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(Section)
    if program_id is not None:
        q = q.filter(Section.program_id == program_id)
    return q.order_by(Section.id).all()


@router.get("/{section_id}", response_model=SectionOut, dependencies=[Depends(require_read_access)])
def get_section(section_id: int, db: Session = Depends(get_db)):
    return _get_section_or_404(db, section_id)


@router.post("", response_model=SectionOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_write_access)])
def create_section(payload: SectionCreate, db: Session = Depends(get_db)):
    _check_fks(db, payload.program_id, payload.time_structure_id)
    section = Section(**payload.model_dump())
    db.add(section)
    db.commit()
    db.refresh(section)
    return section


@router.put("/{section_id}", response_model=SectionOut, dependencies=[Depends(require_write_access)])
def update_section(section_id: int, payload: SectionUpdate, db: Session = Depends(get_db)):
    section = _get_section_or_404(db, section_id)
    data = payload.model_dump(exclude_unset=True)
    _check_fks(db, data.get("program_id"), data.get("time_structure_id"))
    for field, value in data.items():
        setattr(section, field, value)
    db.commit()
    db.refresh(section)
    return section


@router.delete("/{section_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_write_access)])
def delete_section(section_id: int, db: Session = Depends(get_db)):
    section = _get_section_or_404(db, section_id)
    db.delete(section)
    db.commit()
    return None


# ---- Nested lab-batches ----

@router.get("/{section_id}/lab-batches", response_model=list[LabBatchOut],
            dependencies=[Depends(require_read_access)])
def list_lab_batches(section_id: int, db: Session = Depends(get_db)):
    _get_section_or_404(db, section_id)
    return db.query(LabBatch).filter(LabBatch.section_id == section_id).order_by(LabBatch.id).all()


@router.post("/{section_id}/lab-batches", response_model=LabBatchOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_write_access)])
def create_lab_batch(section_id: int, payload: LabBatchNestedCreate, db: Session = Depends(get_db)):
    _get_section_or_404(db, section_id)
    batch = LabBatch(section_id=section_id, **payload.model_dump())
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


@router.put("/{section_id}/lab-batches/{batch_id}", response_model=LabBatchOut,
            dependencies=[Depends(require_write_access)])
def update_lab_batch(section_id: int, batch_id: int, payload: LabBatchUpdate, db: Session = Depends(get_db)):
    _get_section_or_404(db, section_id)
    batch = db.get(LabBatch, batch_id)
    if batch is None or batch.section_id != section_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LabBatch not found")
    data = payload.model_dump(exclude_unset=True)
    if data.get("section_id") is not None and db.get(Section, data["section_id"]) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    for field, value in data.items():
        setattr(batch, field, value)
    db.commit()
    db.refresh(batch)
    return batch


@router.delete("/{section_id}/lab-batches/{batch_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_write_access)])
def delete_lab_batch(section_id: int, batch_id: int, db: Session = Depends(get_db)):
    _get_section_or_404(db, section_id)
    batch = db.get(LabBatch, batch_id)
    if batch is None or batch.section_id != section_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LabBatch not found")
    db.delete(batch)
    db.commit()
    return None


# ---- Flat lab-batches router (direct access by id, filterable by section_id) ----

lab_batches_router = APIRouter(prefix="/api/lab-batches", tags=["lab-batches"])


@lab_batches_router.get("", response_model=list[LabBatchOut], dependencies=[Depends(require_read_access)])
def list_all_lab_batches(section_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(LabBatch)
    if section_id is not None:
        q = q.filter(LabBatch.section_id == section_id)
    return q.order_by(LabBatch.id).all()


@lab_batches_router.get("/{batch_id}", response_model=LabBatchOut, dependencies=[Depends(require_read_access)])
def get_lab_batch(batch_id: int, db: Session = Depends(get_db)):
    batch = db.get(LabBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LabBatch not found")
    return batch
