from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class WeightProfileBase(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    is_preset: bool = False
    weights: dict[str, float] = Field(default_factory=dict)


class WeightProfileCreate(WeightProfileBase):
    pass


class WeightProfileUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=80)
    is_preset: Optional[bool] = None
    weights: Optional[dict[str, float]] = None


class WeightProfileOut(WeightProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
