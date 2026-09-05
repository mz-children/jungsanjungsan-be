import uuid

from sqlalchemy.orm import Session

from src.rooms.model import Room


def get_by_id(
    db: Session,
    room_id: uuid.UUID,
) -> Room | None:
    return db.get(Room, room_id)


def find_by_share_code(
    db: Session,
    share_code: str,
) -> Room | None:
    return db.query(Room).filter(Room.share_code == share_code).first()


def save(
    db: Session,
    room: Room,
) -> Room:
    db.add(room)
    db.commit()
    db.refresh(room)

    return room


def delete(
    db: Session,
    room: Room,
) -> None:
    db.delete(room)
    db.commit()
