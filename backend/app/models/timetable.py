from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, utcnow
from app.models.enums import SessionKind, VersionStatus


class TimetableVersion(Base, TimestampMixin):
    __tablename__ = "timetable_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    status: Mapped[VersionStatus] = mapped_column(Enum(VersionStatus), default=VersionStatus.DRAFT)
    parent_version_id: Mapped[int | None] = mapped_column(ForeignKey("timetable_versions.id"), nullable=True)
    weight_profile_id: Mapped[int | None] = mapped_column(ForeignKey("weight_profiles.id"), nullable=True)
    stability_weight: Mapped[float] = mapped_column(Integer, default=0)
    created_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    hard_violations: Mapped[int] = mapped_column(Integer, default=0)
    soft_score: Mapped[float] = mapped_column(Integer, default=0)
    solve_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    scorecard: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    sessions: Mapped[list["TimetableSession"]] = relationship(
        back_populates="version", cascade="all, delete-orphan"
    )
    unplaced: Mapped[list["UnplacedRequirement"]] = relationship(
        back_populates="version", cascade="all, delete-orphan"
    )


class TimetableSession(Base, TimestampMixin):
    __tablename__ = "timetable_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("timetable_versions.id"))
    session_kind: Mapped[SessionKind] = mapped_column(Enum(SessionKind), default=SessionKind.REGULAR)
    day_index: Mapped[int] = mapped_column(Integer)
    period_index: Mapped[int] = mapped_column(Integer)  # first period of the block
    num_periods: Mapped[int] = mapped_column(Integer, default=1)

    subject_id: Mapped[int | None] = mapped_column(ForeignKey("subjects.id"), nullable=True)
    teacher_id: Mapped[int | None] = mapped_column(ForeignKey("teachers.id"), nullable=True)
    room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id"), nullable=True)
    lab_batch_id: Mapped[int | None] = mapped_column(ForeignKey("lab_batches.id"), nullable=True)

    allocation_id: Mapped[int | None] = mapped_column(ForeignKey("allocations.id"), nullable=True)
    elective_basket_id: Mapped[int | None] = mapped_column(ForeignKey("elective_baskets.id"), nullable=True)
    elective_option_id: Mapped[int | None] = mapped_column(ForeignKey("elective_options.id"), nullable=True)
    combined_class_id: Mapped[int | None] = mapped_column(ForeignKey("combined_classes.id"), nullable=True)

    # Rows sharing a sync_group are, by construction, meant to occur at the same slot
    # (e.g. parallel elective-basket options) and are not a section double-booking conflict.
    sync_group: Mapped[str | None] = mapped_column(String(60), nullable=True)

    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)

    version: Mapped[TimetableVersion] = relationship(back_populates="sessions")
    subject = relationship("Subject")
    teacher = relationship("Teacher")
    room = relationship("Room")
    lab_batch = relationship("LabBatch")
    allocation = relationship("Allocation")
    section_links: Mapped[list["SessionSection"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class SessionSection(Base):
    """Which sections are occupied (cannot be scheduled elsewhere) by a given session."""

    __tablename__ = "session_sections"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("timetable_sessions.id"))
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id"))

    session: Mapped[TimetableSession] = relationship(back_populates="section_links")
    section = relationship("Section")


class UnplacedRequirement(Base):
    __tablename__ = "unplaced_requirements"

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("timetable_versions.id"))
    description: Mapped[str] = mapped_column(Text)
    allocation_id: Mapped[int | None] = mapped_column(ForeignKey("allocations.id"), nullable=True)
    elective_basket_id: Mapped[int | None] = mapped_column(ForeignKey("elective_baskets.id"), nullable=True)
    combined_class_id: Mapped[int | None] = mapped_column(ForeignKey("combined_classes.id"), nullable=True)
    sessions_missing: Mapped[int] = mapped_column(Integer, default=1)

    version: Mapped[TimetableVersion] = relationship(back_populates="unplaced")
