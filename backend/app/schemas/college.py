from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DepartmentBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=20)


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    code: Optional[str] = Field(default=None, min_length=1, max_length=20)


class DepartmentOut(DepartmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class ProgramBase(BaseModel):
    department_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=20)
    duration_semesters: int = Field(default=8, gt=0, le=20)
    time_structure_id: Optional[int] = Field(default=None, gt=0)


class ProgramCreate(ProgramBase):
    pass


class ProgramUpdate(BaseModel):
    department_id: Optional[int] = Field(default=None, gt=0)
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    code: Optional[str] = Field(default=None, min_length=1, max_length=20)
    duration_semesters: Optional[int] = Field(default=None, gt=0, le=20)
    time_structure_id: Optional[int] = Field(default=None, gt=0)


class ProgramOut(ProgramBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class SectionBase(BaseModel):
    program_id: int = Field(gt=0)
    semester_number: int = Field(gt=0, le=20)
    name: str = Field(min_length=1, max_length=40)
    strength: int = Field(default=60, gt=0)
    time_structure_id: Optional[int] = Field(default=None, gt=0)
    max_periods_per_day: Optional[int] = Field(default=None, gt=0)
    max_consecutive_periods: Optional[int] = Field(default=None, gt=0)


class SectionCreate(SectionBase):
    pass


class SectionUpdate(BaseModel):
    program_id: Optional[int] = Field(default=None, gt=0)
    semester_number: Optional[int] = Field(default=None, gt=0, le=20)
    name: Optional[str] = Field(default=None, min_length=1, max_length=40)
    strength: Optional[int] = Field(default=None, gt=0)
    time_structure_id: Optional[int] = Field(default=None, gt=0)
    max_periods_per_day: Optional[int] = Field(default=None, gt=0)
    max_consecutive_periods: Optional[int] = Field(default=None, gt=0)


class SectionOut(SectionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class LabBatchBase(BaseModel):
    section_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=40)
    strength: int = Field(default=30, gt=0)


class LabBatchCreate(LabBatchBase):
    pass


class LabBatchNestedCreate(BaseModel):
    """For POST /sections/{section_id}/lab-batches, where section_id comes from the path."""

    name: str = Field(min_length=1, max_length=40)
    strength: int = Field(default=30, gt=0)


class LabBatchUpdate(BaseModel):
    section_id: Optional[int] = Field(default=None, gt=0)
    name: Optional[str] = Field(default=None, min_length=1, max_length=40)
    strength: Optional[int] = Field(default=None, gt=0)


class LabBatchOut(LabBatchBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
