from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PreferenceType


class TeacherBase(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=120)
    department_id: int = Field(gt=0)
    email: Optional[str] = Field(default=None, max_length=150)
    phone: Optional[str] = Field(default=None, max_length=30)
    max_periods_per_day: int = Field(default=6, gt=0, le=12)
    max_periods_per_week: int = Field(default=24, gt=0, le=60)
    max_consecutive_periods: int = Field(default=4, gt=0, le=12)
    is_visiting: bool = False
    visiting_days: Optional[list[int]] = None


class TeacherCreate(TeacherBase):
    pass


class TeacherUpdate(BaseModel):
    code: Optional[str] = Field(default=None, min_length=1, max_length=20)
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    department_id: Optional[int] = Field(default=None, gt=0)
    email: Optional[str] = Field(default=None, max_length=150)
    phone: Optional[str] = Field(default=None, max_length=30)
    max_periods_per_day: Optional[int] = Field(default=None, gt=0, le=12)
    max_periods_per_week: Optional[int] = Field(default=None, gt=0, le=60)
    max_consecutive_periods: Optional[int] = Field(default=None, gt=0, le=12)
    is_visiting: Optional[bool] = None
    visiting_days: Optional[list[int]] = None


class TeacherOut(TeacherBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class TeacherSubjectBase(BaseModel):
    teacher_id: int = Field(gt=0)
    subject_id: int = Field(gt=0)


class TeacherSubjectNestedCreate(BaseModel):
    """For POST /teachers/{teacher_id}/subjects, where teacher_id comes from the path."""

    subject_id: int = Field(gt=0)


class TeacherSubjectCreate(TeacherSubjectBase):
    pass


class TeacherSubjectOut(TeacherSubjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class TeacherUnavailabilityBase(BaseModel):
    teacher_id: int = Field(gt=0)
    day_index: int = Field(ge=0, le=6)
    period_index: Optional[int] = Field(default=None, ge=0)


class TeacherUnavailabilityNestedCreate(BaseModel):
    day_index: int = Field(ge=0, le=6)
    period_index: Optional[int] = Field(default=None, ge=0)


class TeacherUnavailabilityCreate(TeacherUnavailabilityBase):
    pass


class TeacherUnavailabilityOut(TeacherUnavailabilityBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class TeacherPreferenceBase(BaseModel):
    teacher_id: int = Field(gt=0)
    preference_type: PreferenceType
    day_index: Optional[int] = Field(default=None, ge=0, le=6)
    weight: float = Field(default=1.0, ge=0)


class TeacherPreferenceNestedCreate(BaseModel):
    preference_type: PreferenceType
    day_index: Optional[int] = Field(default=None, ge=0, le=6)
    weight: float = Field(default=1.0, ge=0)


class TeacherPreferenceCreate(TeacherPreferenceBase):
    pass


class TeacherPreferenceUpdate(BaseModel):
    preference_type: Optional[PreferenceType] = None
    day_index: Optional[int] = Field(default=None, ge=0, le=6)
    weight: Optional[float] = Field(default=None, ge=0)


class TeacherPreferenceOut(TeacherPreferenceBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
