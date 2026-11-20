from sqlalchemy import Boolean, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# Keys here are exactly the soft terms the solver's objective (app/solver/model.py) knows
# how to compute. Keep this list and the objective builder in sync.
DEFAULT_WEIGHTS = {
    "section_gaps": 10,
    "teacher_gaps": 8,
    "same_subject_twice_a_day": 12,
    "section_daily_balance": 6,
    "teacher_workload_balance": 8,
    "teacher_preferred_day": 5,
    "teacher_free_day": 6,
    "teacher_no_first_period": 4,
    "teacher_no_last_period": 3,
    "teacher_avoid_back_to_back": 3,
    "lab_afternoon_preference": 4,
    "heavy_subject_last_period": 4,
    "stability": 15,
}

PRESETS = {
    "balanced": dict(DEFAULT_WEIGHTS),
    "student_comfort_first": {
        **DEFAULT_WEIGHTS,
        "section_gaps": 20,
        "section_daily_balance": 14,
        "same_subject_twice_a_day": 18,
        "heavy_subject_last_period": 10,
        "teacher_workload_balance": 4,
        "teacher_preferred_day": 2,
        "teacher_free_day": 2,
    },
    "teacher_convenience_first": {
        **DEFAULT_WEIGHTS,
        "teacher_gaps": 18,
        "teacher_workload_balance": 16,
        "teacher_preferred_day": 12,
        "teacher_free_day": 14,
        "teacher_no_first_period": 10,
        "teacher_avoid_back_to_back": 10,
        "section_gaps": 6,
    },
}


class WeightProfile(Base):
    __tablename__ = "weight_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    is_preset: Mapped[bool] = mapped_column(Boolean, default=False)
    weights: Mapped[dict] = mapped_column(JSON, default=dict)
