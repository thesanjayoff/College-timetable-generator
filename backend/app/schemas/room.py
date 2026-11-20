from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import RoomType


class RoomBase(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=120)
    room_type: RoomType
    capacity: int = Field(default=60, gt=0)
    lab_category: Optional[str] = Field(default=None, max_length=60)
    equipment_tags: Optional[list[str]] = None
    building: Optional[str] = Field(default=None, max_length=60)
    floor: Optional[int] = None


class RoomCreate(RoomBase):
    pass


class RoomUpdate(BaseModel):
    code: Optional[str] = Field(default=None, min_length=1, max_length=20)
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    room_type: Optional[RoomType] = None
    capacity: Optional[int] = Field(default=None, gt=0)
    lab_category: Optional[str] = Field(default=None, max_length=60)
    equipment_tags: Optional[list[str]] = None
    building: Optional[str] = Field(default=None, max_length=60)
    floor: Optional[int] = None


class RoomOut(RoomBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class RoomUnavailabilityBase(BaseModel):
    room_id: int = Field(gt=0)
    day_index: int = Field(ge=0, le=6)
    period_index: Optional[int] = Field(default=None, ge=0)


class RoomUnavailabilityNestedCreate(BaseModel):
    day_index: int = Field(ge=0, le=6)
    period_index: Optional[int] = Field(default=None, ge=0)


class RoomUnavailabilityCreate(RoomUnavailabilityBase):
    pass


class RoomUnavailabilityOut(RoomUnavailabilityBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
