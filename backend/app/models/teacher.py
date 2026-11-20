from sqlalchemy import Boolean, Enum, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import PreferenceType


class Teacher(Base):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    email: Mapped[str | None] = mapped_column(String(150), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    max_periods_per_day: Mapped[int] = mapped_column(Integer, default=6)
    max_periods_per_week: Mapped[int] = mapped_column(Integer, default=24)
    max_consecutive_periods: Mapped[int] = mapped_column(Integer, default=4)
    is_visiting: Mapped[bool] = mapped_column(Boolean, default=False)
    # For visiting faculty: list of allowed day_index values. Empty/None = all days.
    visiting_days: Mapped[list | None] = mapped_column(JSON, nullable=True)

    department = relationship("Department")
    subjects: Mapped[list["TeacherSubject"]] = relationship(back_populates="teacher", cascade="all, delete-orphan")
    unavailability: Mapped[list["TeacherUnavailability"]] = relationship(
        back_populates="teacher", cascade="all, delete-orphan"
    )
    preferences: Mapped[list["TeacherPreference"]] = relationship(
        back_populates="teacher", cascade="all, delete-orphan"
    )


class TeacherSubject(Base):
    __tablename__ = "teacher_subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"))
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))

    teacher: Mapped[Teacher] = relationship(back_populates="subjects")
    subject = relationship("Subject")


class TeacherUnavailability(Base):
    __tablename__ = "teacher_unavailability"

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"))
    day_index: Mapped[int] = mapped_column(Integer)
    period_index: Mapped[int | None] = mapped_column(Integer, nullable=True)  # None = whole day unavailable

    teacher: Mapped[Teacher] = relationship(back_populates="unavailability")


class TeacherPreference(Base):
    __tablename__ = "teacher_preferences"

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"))
    preference_type: Mapped[PreferenceType] = mapped_column(Enum(PreferenceType))
    day_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0)

    teacher: Mapped[Teacher] = relationship(back_populates="preferences")
