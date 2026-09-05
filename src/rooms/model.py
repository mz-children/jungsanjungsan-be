import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base
from src.core.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class RoomStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SETTLED = "SETTLED"


class Room(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """정산방. `share_code`가 URL 노출용 공개 식별자이며 내부 `id`는 응답에 노출하지 않는다."""

    __tablename__ = "room"

    share_code: Mapped[str] = mapped_column(Text, unique=True)
    title: Mapped[str] = mapped_column(Text)
    total_budget: Mapped[int] = mapped_column(BigInteger)
    thumbnail_file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("file_object.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[RoomStatus] = mapped_column(
        Enum(RoomStatus, name="room_status", native_enum=True),
        server_default=RoomStatus.ACTIVE.value,
    )
    settled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        CheckConstraint("btrim(title) <> ''", name="room_title_not_blank"),
        CheckConstraint("char_length(title) <= 50", name="room_title_len"),
        CheckConstraint("total_budget >= 0", name="room_budget_nonneg"),
        CheckConstraint(
            "share_code ~ '^[A-Za-z0-9_-]{8,32}$'", name="room_share_code_fmt"
        ),
        CheckConstraint(
            "(status = 'SETTLED' AND settled_at IS NOT NULL) "
            "OR (status = 'ACTIVE' AND settled_at IS NULL)",
            name="room_settled_consistency",
        ),
    )
