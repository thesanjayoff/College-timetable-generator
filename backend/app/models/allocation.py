from sqlalchemy import Boolean, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Allocation(Base):
    """A single teaching requirement: subject taught to a section (or one of its lab batches)."""

    __tablename__ = "allocations"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id"))
    lab_batch_id: Mapped[int | None] = mapped_column(ForeignKey("lab_batches.id"), nullable=True)
    teacher_id: Mapped[int | None] = mapped_column(ForeignKey("teachers.id"), nullable=True)
    is_fixed_teacher: Mapped[bool] = mapped_column(Boolean, default=False)
    room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id"), nullable=True)
    is_fixed_room: Mapped[bool] = mapped_column(Boolean, default=False)

    subject = relationship("Subject")
    section = relationship("Section")
    lab_batch = relationship("LabBatch")
    teacher = relationship("Teacher")
    room = relationship("Room")
