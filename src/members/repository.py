import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.members.model import Member


def get_by_id(
    db: Session,
    member_id: uuid.UUID,
) -> Member | None:
    return db.scalars(
        select(Member).where(Member.id == member_id, Member.deleted_at.is_(None))
    ).first()


def get_active_in_room(
    db: Session,
    room_id: uuid.UUID,
    member_id: uuid.UUID,
) -> Member | None:
    return db.scalars(
        select(Member).where(
            Member.id == member_id,
            Member.room_id == room_id,
            Member.deleted_at.is_(None),
        )
    ).first()


def list_by_room(
    db: Session,
    room_id: uuid.UUID,
) -> list[Member]:
    return db.scalars(
        select(Member)
        .where(Member.room_id == room_id, Member.deleted_at.is_(None))
        .order_by(Member.display_order, Member.created_at)
    ).all()


def save(
    db: Session,
    member: Member,
) -> Member:
    db.add(member)
    db.commit()
    db.refresh(member)

    return member


def save_many(
    db: Session,
    members: list[Member],
) -> list[Member]:
    db.add_all(members)
    db.commit()

    for member in members:
        db.refresh(member)

    return members


def soft_delete(
    db: Session,
    member: Member,
) -> Member:
    member.deleted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(member)

    return member
