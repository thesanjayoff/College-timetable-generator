from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import RoomType


class CombinedClassBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    subject_id: int = Field(gt=0)
    teacher_id: Optional[int] = Field(default=None, gt=0)
    sessions_per_week: int = Field(default=1, gt=0, le=40)
    block_size: int = Field(default=1, gt=0, le=10)
    room_type_required: RoomType = RoomType.SEMINAR_HALL


class CombinedClassCreate(CombinedClassBase):
    pass


class CombinedClassUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    subject_id: Optional[int] = Field(default=None, gt=0)
    teacher_id: Optional[int] = Field(default=None, gt=0)
    sessions_per_week: Optional[int] = Field(default=None, gt=0, le=40)
    block_size: Optional[int] = Field(default=None, gt=0, le=10)
    room_type_required: Optional[RoomType] = None


class CombinedClassOut(CombinedClassBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class CombinedClassSectionBase(BaseModel):
    combined_class_id: int = Field(gt=0)
    section_id: int = Field(gt=0)


class CombinedClassSectionNestedCreate(BaseModel):
    """For POST /combined-classes/{combined_class_id}/sections, path supplies combined_class_id."""

    section_id: int = Field(gt=0)


class CombinedClassSectionCreate(CombinedClassSectionBase):
    pass


class CombinedClassSectionOut(CombinedClassSectionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
