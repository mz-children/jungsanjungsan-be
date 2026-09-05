import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.settlements.model import Settlement, SettlementEntry


def find_by_room_id(
    db: Session,
    room_id: uuid.UUID,
) -> Settlement | None:
    return db.scalars(
        select(Settlement).where(Settlement.room_id == room_id)
    ).first()


def save(
    db: Session,
    settlement: Settlement,
) -> Settlement:
    db.add(settlement)
    db.commit()
    db.refresh(settlement)

    return settlement


def list_entries_by_settlement(
    db: Session,
    settlement_id: uuid.UUID,
) -> list[SettlementEntry]:
    return db.scalars(
        select(SettlementEntry).where(SettlementEntry.settlement_id == settlement_id)
    ).all()


def save_entries(
    db: Session,
    entries: list[SettlementEntry],
) -> list[SettlementEntry]:
    db.add_all(entries)
    db.commit()

    for entry in entries:
        db.refresh(entry)

    return entries
