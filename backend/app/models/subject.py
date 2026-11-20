from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import SubjectType


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    subject_type: Mapped[SubjectType] = mapped_column(Enum(SubjectType))
    credits: Mapped[float] = mapped_column(Integer, default=3)
    # Total periods/week this subject needs for a section.
    periods_per_week: Mapped[int] = mapped_column(Integer, default=3)
    # Number of distinct timetable sessions/week (e.g. a 4-period lab might be 2 sessions of 2 periods).
    sessions_per_week: Mapped[int] = mapped_column(Integer, default=3)
    # Consecutive periods per session (1 for theory, 2-3 for labs).
    block_size: Mapped[int] = mapped_column(Integer, default=1)
    spread_across_days: Mapped[bool] = mapped_column(Boolean, default=True)
    max_per_day: Mapped[int] = mapped_column(Integer, default=1)
    requires_lab_batches: Mapped[bool] = mapped_column(Boolean, default=False)
    avoid_last_period: Mapped[bool] = mapped_column(Boolean, default=False)
    prefer_afternoon: Mapped[bool] = mapped_column(Boolean, default=False)

    department = relationship("Department")

    @property
    def is_lab(self) -> bool:
        return self.subject_type == SubjectType.LAB
