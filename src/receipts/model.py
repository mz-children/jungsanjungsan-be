import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base
from src.core.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Receipt(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """결제 내역. `payer_member_id`는 `(room_id, id)` 복합 FK로 걸어 다른 방의 멤버를 결제자로
    지정할 수 없도록 DB가 보장한다."""

    __tablename__ = "receipt"

    room_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    payer_member_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    merchant: Mapped[str] = mapped_column(Text)
    amount: Mapped[int] = mapped_column(BigInteger)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["room_id"], ["room.id"], ondelete="CASCADE", name="receipt_room_fk"
        ),
        ForeignKeyConstraint(
            ["room_id", "payer_member_id"],
            ["member.room_id", "member.id"],
            ondelete="RESTRICT",
            name="receipt_payer_fk",
        ),
        ForeignKeyConstraint(
            ["image_file_id"],
            ["file_object.id"],
            ondelete="SET NULL",
            name="receipt_image_fk",
        ),
        CheckConstraint("amount > 0", name="receipt_amount_pos"),
        CheckConstraint("btrim(merchant) <> ''", name="receipt_merchant_not_blank"),
        CheckConstraint("char_length(merchant) <= 100", name="receipt_merchant_len"),
        CheckConstraint(
            "description IS NULL OR char_length(description) <= 500",
            name="receipt_desc_len",
        ),
        Index(
            "receipt_idx_room_recent",
            "room_id",
            text("paid_at DESC"),
            text("id DESC"),
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "receipt_idx_room_payer_recent",
            "room_id",
            "payer_member_id",
            text("paid_at DESC"),
            text("id DESC"),
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )
