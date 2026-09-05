import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base
from src.core.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class Settlement(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    """정산 완료 시점의 계산 결과 스냅샷. 이후 room/member가 바뀌어도 값은 고정된다.
    `UNIQUE(room_id)`로 방 하나당 중복 정산을 구조적으로 차단한다."""

    __tablename__ = "settlement"

    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("room.id", ondelete="CASCADE"), unique=True
    )
    room_title: Mapped[str] = mapped_column(Text)
    budget_amount: Mapped[int] = mapped_column(BigInteger)
    period_start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    period_end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    total_amount: Mapped[int] = mapped_column(BigInteger)
    member_count: Mapped[int] = mapped_column(Integer)
    per_person_amount: Mapped[int] = mapped_column(BigInteger)
    receipt_count: Mapped[int] = mapped_column(Integer)

    __table_args__ = (
        CheckConstraint("member_count > 0", name="settlement_member_count_pos"),
        CheckConstraint("total_amount >= 0", name="settlement_total_nonneg"),
        CheckConstraint("receipt_count >= 0", name="settlement_receipts_nonneg"),
        CheckConstraint(
            "period_end_at >= period_start_at", name="settlement_period_order"
        ),
    )


class SettlementEntry(Base, UUIDPrimaryKeyMixin):
    """멤버별 정산 내역. `balance_amount`는 DB가 계산하는 GENERATED 컬럼이다.
    `sum(balance_amount) = 0` 불변식은 행 간 집계라 CHECK로 표현할 수 없으므로
    삽입 직후 애플리케이션에서 반드시 검증해야 한다 (DB_MODEL.md 6.2)."""

    __tablename__ = "settlement_entry"

    settlement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("settlement.id", ondelete="CASCADE")
    )
    member_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("member.id", ondelete="SET NULL"),
        nullable=True,
    )
    member_name: Mapped[str] = mapped_column(Text)
    is_treasurer: Mapped[bool] = mapped_column(Boolean, server_default="false")
    paid_amount: Mapped[int] = mapped_column(BigInteger)
    share_amount: Mapped[int] = mapped_column(BigInteger)
    balance_amount: Mapped[int] = mapped_column(
        BigInteger, Computed("paid_amount - share_amount", persisted=True)
    )

    __table_args__ = (
        UniqueConstraint("settlement_id", "member_id", name="settlement_entry_uq"),
        CheckConstraint("paid_amount >= 0", name="settlement_entry_paid_pos"),
        CheckConstraint("share_amount >= 0", name="settlement_entry_share_pos"),
    )
