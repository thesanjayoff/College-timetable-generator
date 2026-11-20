from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PeriodKind


class WorkingDayBase(BaseModel):
    day_index: int = Field(ge=0, le=6)
    name: str = Field(min_length=1, max_length=20)
    max_period_index: Optional[int] = Field(default=None, ge=0)


class WorkingDayNestedCreate(WorkingDayBase):
    """For use nested inside a TimeStructureCreate or POST .../working-days."""

    pass


class WorkingDayCreate(WorkingDayBase):
    time_structure_id: int = Field(gt=0)


class WorkingDayUpdate(BaseModel):
    day_index: Optional[int] = Field(default=None, ge=0, le=6)
    name: Optional[str] = Field(default=None, min_length=1, max_length=20)
    max_period_index: Optional[int] = Field(default=None, ge=0)


class WorkingDayOut(WorkingDayBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    time_structure_id: int


class PeriodSlotBase(BaseModel):
    period_index: int = Field(ge=0)
    label: str = Field(min_length=1, max_length=40)
    start_time: str = Field(min_length=1, max_length=10)
    end_time: str = Field(min_length=1, max_length=10)
    kind: PeriodKind = PeriodKind.TEACHING
    teaching_order: Optional[int] = Field(default=None, ge=0)


class PeriodSlotNestedCreate(PeriodSlotBase):
    """For use nested inside a TimeStructureCreate or POST .../periods."""

    pass


class PeriodSlotCreate(PeriodSlotBase):
    time_structure_id: int = Field(gt=0)


class PeriodSlotUpdate(BaseModel):
    period_index: Optional[int] = Field(default=None, ge=0)
    label: Optional[str] = Field(default=None, min_length=1, max_length=40)
    start_time: Optional[str] = Field(default=None, min_length=1, max_length=10)
    end_time: Optional[str] = Field(default=None, min_length=1, max_length=10)
    kind: Optional[PeriodKind] = None
    teaching_order: Optional[int] = Field(default=None, ge=0)


class PeriodSlotOut(PeriodSlotBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    time_structure_id: int


class TimeStructureBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    is_default: bool = False


class TimeStructureCreate(TimeStructureBase):
    """Creating a TimeStructure can include its days/periods inline."""

    days: list[WorkingDayNestedCreate] = Field(default_factory=list)
    periods: list[PeriodSlotNestedCreate] = Field(default_factory=list)


class TimeStructureUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    is_default: Optional[bool] = None


class TimeStructureOut(TimeStructureBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    days: list[WorkingDayOut] = Field(default_factory=list)
    periods: list[PeriodSlotOut] = Field(default_factory=list)
