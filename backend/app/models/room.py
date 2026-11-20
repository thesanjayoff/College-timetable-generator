from sqlalchemy import Enum, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import RoomType


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    room_type: Mapped[RoomType] = mapped_column(Enum(RoomType))
    capacity: Mapped[int] = mapped_column(Integer, default=60)
    lab_category: Mapped[str | None] = mapped_column(String(60), nullable=True)
    equipment_tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    building: Mapped[str | None] = mapped_column(String(60), nullable=True)
    floor: Mapped[int | None] = mapped_column(Integer, nullable=True)

    unavailability: Mapped[list["RoomUnavailability"]] = relationship(
        back_populates="room", cascade="all, delete-orphan"
    )


class RoomUnavailability(Base):
    __tablename__ = "room_unavailability"

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"))
    day_index: Mapped[int] = mapped_column(Integer)
    period_index: Mapped[int | None] = mapped_column(Integer, nullable=True)

    room: Mapped[Room] = relationship(back_populates="unavailability")
