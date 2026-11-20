from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import RoomType


class ElectiveBasketBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    sessions_per_week: int = Field(default=3, gt=0, le=40)
    block_size: int = Field(default=1, gt=0, le=10)


class ElectiveBasketCreate(ElectiveBasketBase):
    pass


class ElectiveBasketUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    sessions_per_week: Optional[int] = Field(default=None, gt=0, le=40)
    block_size: Optional[int] = Field(default=None, gt=0, le=10)


class ElectiveBasketOut(ElectiveBasketBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class ElectiveOptionBase(BaseModel):
    basket_id: int = Field(gt=0)
    subject_id: int = Field(gt=0)
    teacher_id: Optional[int] = Field(default=None, gt=0)
    room_type_required: RoomType = RoomType.CLASSROOM
    expected_strength: int = Field(default=30, gt=0)


class ElectiveOptionNestedCreate(BaseModel):
    """For POST /electives/baskets/{basket_id}/options, where basket_id comes from the path."""

    subject_id: int = Field(gt=0)
    teacher_id: Optional[int] = Field(default=None, gt=0)
    room_type_required: RoomType = RoomType.CLASSROOM
    expected_strength: int = Field(default=30, gt=0)


class ElectiveOptionCreate(ElectiveOptionBase):
    pass


class ElectiveOptionUpdate(BaseModel):
    subject_id: Optional[int] = Field(default=None, gt=0)
    teacher_id: Optional[int] = Field(default=None, gt=0)
    room_type_required: Optional[RoomType] = None
    expected_strength: Optional[int] = Field(default=None, gt=0)


class ElectiveOptionOut(ElectiveOptionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class ElectiveParticipationBase(BaseModel):
    basket_id: int = Field(gt=0)
    section_id: int = Field(gt=0)


class ElectiveParticipationNestedCreate(BaseModel):
    """For POST /electives/baskets/{basket_id}/participations, where basket_id comes from the path."""

    section_id: int = Field(gt=0)


class ElectiveParticipationCreate(ElectiveParticipationBase):
    pass


class ElectiveParticipationOut(ElectiveParticipationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
