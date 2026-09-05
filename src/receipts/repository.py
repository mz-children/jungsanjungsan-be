import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, tuple_
from sqlalchemy.orm import Session

from src.receipts.model import Receipt


def get_by_id(
    db: Session,
    receipt_id: uuid.UUID,
) -> Receipt | None:
    return db.scalars(
        select(Receipt).where(Receipt.id == receipt_id, Receipt.deleted_at.is_(None))
    ).first()


def find_by_id_in_room(
    db: Session,
    room_id: uuid.UUID,
    receipt_id: uuid.UUID,
) -> Receipt | None:
    return db.scalars(
        select(Receipt).where(
            Receipt.id == receipt_id,
            Receipt.room_id == room_id,
            Receipt.deleted_at.is_(None),
        )
    ).first()


def list_by_room(
    db: Session,
    room_id: uuid.UUID,
    limit: int = 20,
) -> list[Receipt]:
    return db.scalars(
        select(Receipt)
        .where(Receipt.room_id == room_id, Receipt.deleted_at.is_(None))
        .order_by(Receipt.paid_at.desc(), Receipt.id.desc())
        .limit(limit)
    ).all()


def list_by_room_cursor(
    db: Session,
    room_id: uuid.UUID,
    *,
    payer_member_id: uuid.UUID | None = None,
    q: str | None = None,
    cursor: tuple[datetime, uuid.UUID] | None = None,
    limit: int = 20,
) -> list[Receipt]:
    """결제 내역 리스트 (검색 + 필터 + 무한스크롤). `(paid_at, id)` 튜플 커서로
    OFFSET 없이 페이지네이션한다 (DB_MODEL.md 5.1, `receipt_idx_room_recent` 인덱스)."""

    stmt = select(Receipt).where(
        Receipt.room_id == room_id, Receipt.deleted_at.is_(None)
    )

    if payer_member_id is not None:
        stmt = stmt.where(Receipt.payer_member_id == payer_member_id)

    if q:
        stmt = stmt.where(Receipt.merchant.ilike(f"%{q}%"))

    if cursor is not None:
        cursor_paid_at, cursor_id = cursor
        stmt = stmt.where(
            tuple_(Receipt.paid_at, Receipt.id) < tuple_(cursor_paid_at, cursor_id)
        )

    stmt = stmt.order_by(Receipt.paid_at.desc(), Receipt.id.desc()).limit(limit)

    return db.scalars(stmt).all()


def aggregate_active_by_room(
    db: Session,
    room_id: uuid.UUID,
) -> tuple[int, int]:
    """(결제 총액, 결제 건수)."""

    total, count = db.execute(
        select(func.coalesce(func.sum(Receipt.amount), 0), func.count()).where(
            Receipt.room_id == room_id, Receipt.deleted_at.is_(None)
        )
    ).one()

    return int(total), int(count)


def sum_active_amount_by_payer(
    db: Session,
    room_id: uuid.UUID,
) -> dict[uuid.UUID, int]:
    rows = db.execute(
        select(Receipt.payer_member_id, func.sum(Receipt.amount))
        .where(Receipt.room_id == room_id, Receipt.deleted_at.is_(None))
        .group_by(Receipt.payer_member_id)
    ).all()

    return {row[0]: int(row[1]) for row in rows}


def count_active_by_payer(
    db: Session,
    room_id: uuid.UUID,
) -> dict[uuid.UUID, int]:
    rows = db.execute(
        select(Receipt.payer_member_id, func.count())
        .where(Receipt.room_id == room_id, Receipt.deleted_at.is_(None))
        .group_by(Receipt.payer_member_id)
    ).all()

    return {row[0]: int(row[1]) for row in rows}


def save(
    db: Session,
    receipt: Receipt,
) -> Receipt:
    db.add(receipt)
    db.commit()
    db.refresh(receipt)

    return receipt


def soft_delete(
    db: Session,
    receipt: Receipt,
) -> Receipt:
    receipt.deleted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(receipt)

    return receipt
