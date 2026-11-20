from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_read_access, require_write_access
from app.models.college import Department, Program
from app.models.structure import TimeStructure
from app.schemas.college import ProgramCreate, ProgramOut, ProgramUpdate

router = APIRouter(prefix="/api/programs", tags=["programs"])


def _check_fks(db: Session, department_id: Optional[int] = None, time_structure_id: Optional[int] = None):
    if department_id is not None and db.get(Department, department_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    if time_structure_id is not None and db.get(TimeStructure, time_structure_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TimeStructure not found")


@router.get("", response_model=list[ProgramOut], dependencies=[Depends(require_read_access)])
def list_programs(department_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(Program)
    if department_id is not None:
        q = q.filter(Program.department_id == department_id)
    return q.order_by(Program.id).all()


@router.get("/{program_id}", response_model=ProgramOut, dependencies=[Depends(require_read_access)])
def get_program(program_id: int, db: Session = Depends(get_db)):
    program = db.get(Program, program_id)
    if program is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")
    return program


@router.post("", response_model=ProgramOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_write_access)])
def create_program(payload: ProgramCreate, db: Session = Depends(get_db)):
    _check_fks(db, payload.department_id, payload.time_structure_id)
    program = Program(**payload.model_dump())
    db.add(program)
    db.commit()
    db.refresh(program)
    return program


@router.put("/{program_id}", response_model=ProgramOut, dependencies=[Depends(require_write_access)])
def update_program(program_id: int, payload: ProgramUpdate, db: Session = Depends(get_db)):
    program = db.get(Program, program_id)
    if program is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")
    data = payload.model_dump(exclude_unset=True)
    _check_fks(db, data.get("department_id"), data.get("time_structure_id"))
    for field, value in data.items():
        setattr(program, field, value)
    db.commit()
    db.refresh(program)
    return program


@router.delete("/{program_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_write_access)])
def delete_program(program_id: int, db: Session = Depends(get_db)):
    program = db.get(Program, program_id)
    if program is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")
    db.delete(program)
    db.commit()
    return None
