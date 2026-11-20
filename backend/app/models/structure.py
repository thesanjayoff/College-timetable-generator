from sqlalchemy import Boolean, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import PeriodKind


class TimeStructure(Base):
    __tablename__ = "time_structures"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    days: Mapped[list["WorkingDay"]] = relationship(
        back_populates="time_structure", cascade="all, delete-orphan", order_by="WorkingDay.day_index"
    )
    periods: Mapped[list["PeriodSlot"]] = relationship(
        back_populates="time_structure", cascade="all, delete-orphan", order_by="PeriodSlot.period_index"
    )

    def teaching_period_indices(self) -> list[int]:
        return [p.period_index for p in self.periods if p.kind == PeriodKind.TEACHING]

    def max_period_for_day(self, day_index: int) -> int | None:
        for d in self.days:
            if d.day_index == day_index:
                return d.max_period_index
        return None


class WorkingDay(Base):
    __tablename__ = "working_days"

    id: Mapped[int] = mapped_column(primary_key=True)
    time_structure_id: Mapped[int] = mapped_column(ForeignKey("time_structures.id"))
    day_index: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(20))
    # None = full day. Otherwise, only periods with period_index <= this are available (half-day Saturday).
    max_period_index: Mapped[int | None] = mapped_column(Integer, nullable=True)

    time_structure: Mapped[TimeStructure] = relationship(back_populates="days")


class PeriodSlot(Base):
    __tablename__ = "period_slots"

    id: Mapped[int] = mapped_column(primary_key=True)
    time_structure_id: Mapped[int] = mapped_column(ForeignKey("time_structures.id"))
    period_index: Mapped[int] = mapped_column(Integer)
    label: Mapped[str] = mapped_column(String(40))
    start_time: Mapped[str] = mapped_column(String(10))
    end_time: Mapped[str] = mapped_column(String(10))
    kind: Mapped[PeriodKind] = mapped_column(Enum(PeriodKind), default=PeriodKind.TEACHING)
    # Sequential index among teaching-only periods in the day; used for "last period" style soft rules.
    teaching_order: Mapped[int | None] = mapped_column(Integer, nullable=True)

    time_structure: Mapped[TimeStructure] = relationship(back_populates="periods")
