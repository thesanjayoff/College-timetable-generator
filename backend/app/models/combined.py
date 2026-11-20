from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import RoomType


class CombinedClass(Base):
    """A subject taught jointly to several sections/departments in one session."""

    __tablename__ = "combined_classes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    teacher_id: Mapped[int | None] = mapped_column(ForeignKey("teachers.id"), nullable=True)
    sessions_per_week: Mapped[int] = mapped_column(Integer, default=1)
    block_size: Mapped[int] = mapped_column(Integer, default=1)
    room_type_required: Mapped[RoomType] = mapped_column(Enum(RoomType), default=RoomType.SEMINAR_HALL)

    subject = relationship("Subject")
    teacher = relationship("Teacher")
    sections: Mapped[list["CombinedClassSection"]] = relationship(
        back_populates="combined_class", cascade="all, delete-orphan"
    )


class CombinedClassSection(Base):
    __tablename__ = "combined_class_sections"

    id: Mapped[int] = mapped_column(primary_key=True)
    combined_class_id: Mapped[int] = mapped_column(ForeignKey("combined_classes.id"))
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id"))

    combined_class: Mapped[CombinedClass] = relationship(back_populates="sections")
    section = relationship("Section")
