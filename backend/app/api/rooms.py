from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_read_access, require_write_access
from app.models.room import Room, RoomUnavailability
from app.schemas.room import (
    RoomCreate,
    RoomOut,
    RoomUnavailabilityNestedCreate,
    RoomUnavailabilityOut,
    RoomUpdate,
)

router = APIRouter(prefix="/api/rooms", tags=["rooms"])


def _get_room_or_404(db: Session, room_id: int) -> Room:
    room = db.get(Room, room_id)
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    return room


@router.get("", response_model=list[RoomOut], dependencies=[Depends(require_read_access)])
def list_rooms(room_type: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Room)
    if room_type is not None:
        q = q.filter(Room.room_type == room_type)
    return q.order_by(Room.id).all()


@router.get("/{room_id}", response_model=RoomOut, dependencies=[Depends(require_read_access)])
def get_room(room_id: int, db: Session = Depends(get_db)):
    return _get_room_or_404(db, room_id)


@router.post("", response_model=RoomOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_write_access)])
def create_room(payload: RoomCreate, db: Session = Depends(get_db)):
    existing = db.query(Room).filter(Room.code == payload.code).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Room code already exists")
    room = Room(**payload.model_dump())
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


@router.put("/{room_id}", response_model=RoomOut, dependencies=[Depends(require_write_access)])
def update_room(room_id: int, payload: RoomUpdate, db: Session = Depends(get_db)):
    room = _get_room_or_404(db, room_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(room, field, value)
    db.commit()
    db.refresh(room)
    return room


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_write_access)])
def delete_room(room_id: int, db: Session = Depends(get_db)):
    room = _get_room_or_404(db, room_id)
    db.delete(room)
    db.commit()
    return None


# ---- Nested unavailability ----

@router.get("/{room_id}/unavailability", response_model=list[RoomUnavailabilityOut],
            dependencies=[Depends(require_read_access)])
def list_room_unavailability(room_id: int, db: Session = Depends(get_db)):
    _get_room_or_404(db, room_id)
    return db.query(RoomUnavailability).filter(RoomUnavailability.room_id == room_id).order_by(
        RoomUnavailability.id
    ).all()


@router.post("/{room_id}/unavailability", response_model=RoomUnavailabilityOut,
             status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_write_access)])
def add_room_unavailability(
    room_id: int, payload: RoomUnavailabilityNestedCreate, db: Session = Depends(get_db)
):
    _get_room_or_404(db, room_id)
    row = RoomUnavailability(room_id=room_id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{room_id}/unavailability/{row_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_write_access)])
def remove_room_unavailability(room_id: int, row_id: int, db: Session = Depends(get_db)):
    _get_room_or_404(db, room_id)
    row = db.get(RoomUnavailability, row_id)
    if row is None or row.room_id != room_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unavailability entry not found")
    db.delete(row)
    db.commit()
    return None
