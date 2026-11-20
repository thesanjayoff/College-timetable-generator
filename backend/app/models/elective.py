from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import RoomType


class ElectiveBasket(Base):
    __tablename__ = "elective_baskets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    sessions_per_week: Mapped[int] = mapped_column(Integer, default=3)
    block_size: Mapped[int] = mapped_column(Integer, default=1)

    options: Mapped[list["ElectiveOption"]] = relationship(back_populates="basket", cascade="all, delete-orphan")
    participations: Mapped[list["ElectiveParticipation"]] = relationship(
        back_populates="basket", cascade="all, delete-orphan"
    )


class ElectiveOption(Base):
    __tablename__ = "elective_options"

    id: Mapped[int] = mapped_column(primary_key=True)
    basket_id: Mapped[int] = mapped_column(ForeignKey("elective_baskets.id"))
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    teacher_id: Mapped[int | None] = mapped_column(ForeignKey("teachers.id"), nullable=True)
    room_type_required: Mapped[RoomType] = mapped_column(Enum(RoomType), default=RoomType.CLASSROOM)
    expected_strength: Mapped[int] = mapped_column(Integer, default=30)

    basket: Mapped[ElectiveBasket] = relationship(back_populates="options")
    subject = relationship("Subject")
    teacher = relationship("Teacher")


class ElectiveParticipation(Base):
    """Which sections contribute students to a basket (and hence must be free at the basket's slots)."""

    __tablename__ = "elective_participations"

    id: Mapped[int] = mapped_column(primary_key=True)
    basket_id: Mapped[int] = mapped_column(ForeignKey("elective_baskets.id"))
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id"))

    basket: Mapped[ElectiveBasket] = relationship(back_populates="participations")
    section = relationship("Section")
