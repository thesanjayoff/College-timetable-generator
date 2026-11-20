from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import SubjectType


class SubjectBase(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=150)
    department_id: int = Field(gt=0)
    subject_type: SubjectType
    credits: float = Field(default=3, gt=0, le=20)
    periods_per_week: int = Field(default=3, gt=0, le=40)
    sessions_per_week: int = Field(default=3, gt=0, le=40)
    block_size: int = Field(default=1, gt=0, le=10)
    spread_across_days: bool = True
    max_per_day: int = Field(default=1, gt=0, le=10)
    requires_lab_batches: bool = False
    avoid_last_period: bool = False
    prefer_afternoon: bool = False


class SubjectCreate(SubjectBase):
    pass


class SubjectUpdate(BaseModel):
    code: Optional[str] = Field(default=None, min_length=1, max_length=20)
    name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    department_id: Optional[int] = Field(default=None, gt=0)
    subject_type: Optional[SubjectType] = None
    credits: Optional[float] = Field(default=None, gt=0, le=20)
    periods_per_week: Optional[int] = Field(default=None, gt=0, le=40)
    sessions_per_week: Optional[int] = Field(default=None, gt=0, le=40)
    block_size: Optional[int] = Field(default=None, gt=0, le=10)
    spread_across_days: Optional[bool] = None
    max_per_day: Optional[int] = Field(default=None, gt=0, le=10)
    requires_lab_batches: Optional[bool] = None
    avoid_last_period: Optional[bool] = None
    prefer_afternoon: Optional[bool] = None


class SubjectOut(SubjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
