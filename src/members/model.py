import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base
from src.core.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Member(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """여행 멤버. 계정이 아니라 이름표. `receipt`의 복합 FK 대상이라 `UNIQUE(room_id, id)`가 필요하다."""

    __tablename__ = "member"

    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("room.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(Text)
    is_treasurer: Mapped[bool] = mapped_column(Boolean, server_default="false")
    display_order: Mapped[int] = mapped_column(Integer, server_default="0")

    __table_args__ = (
        CheckConstraint("btrim(name) <> ''", name="member_name_not_blank"),
        CheckConstraint("char_length(name) <= 20", name="member_name_len"),
        UniqueConstraint("room_id", "id", name="member_room_id_uq"),
        Index(
            "member_uq_room_name_alive",
            "room_id",
            text("lower(btrim(name))"),
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "member_uq_room_treasurer",
            "room_id",
            unique=True,
            postgresql_where=text("is_treasurer AND deleted_at IS NULL"),
        ),
        Index(
            "member_idx_room_order",
            "room_id",
            "display_order",
            "created_at",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )
