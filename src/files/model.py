from sqlalchemy import BigInteger, CheckConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base
from src.core.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class FileObject(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    """업로드 이미지 메타데이터. 실제 바이너리는 오브젝트 스토리지에 둔다. 하드 삭제."""

    __tablename__ = "file_object"

    storage_key: Mapped[str] = mapped_column(Text, unique=True)
    original_name: Mapped[str] = mapped_column(Text)
    content_type: Mapped[str] = mapped_column(Text)
    byte_size: Mapped[int] = mapped_column(BigInteger)

    __table_args__ = (
        CheckConstraint("byte_size > 0", name="file_object_size_pos"),
        CheckConstraint("content_type LIKE 'image/%'", name="file_object_image_only"),
    )
