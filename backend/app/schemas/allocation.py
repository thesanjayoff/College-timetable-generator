from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AllocationBase(BaseModel):
    subject_id: int = Field(gt=0)
    section_id: int = Field(gt=0)
    lab_batch_id: Optional[int] = Field(default=None, gt=0)
    teacher_id: Optional[int] = Field(default=None, gt=0)
    is_fixed_teacher: bool = False
    room_id: Optional[int] = Field(default=None, gt=0)
    is_fixed_room: bool = False


class AllocationCreate(AllocationBase):
    pass


class AllocationUpdate(BaseModel):
    subject_id: Optional[int] = Field(default=None, gt=0)
    section_id: Optional[int] = Field(default=None, gt=0)
    lab_batch_id: Optional[int] = Field(default=None, gt=0)
    teacher_id: Optional[int] = Field(default=None, gt=0)
    is_fixed_teacher: Optional[bool] = None
    room_id: Optional[int] = Field(default=None, gt=0)
    is_fixed_room: Optional[bool] = None


class AllocationOut(AllocationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
