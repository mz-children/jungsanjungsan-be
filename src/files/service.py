import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from src.config import settings
from src.core.errors import FileTooLargeError, UnsupportedMediaTypeError, ValidationError
from src.files.model import FileObject
from src.files.repository import save

IMAGE_CONTENT_TYPE_PREFIX = "image/"


def _storage_path(storage_key: str) -> Path:
    return Path(settings.FILE_STORAGE_DIR) / storage_key


def to_url(file_object: FileObject) -> str:
    return f"{settings.FILE_BASE_URL}/{file_object.storage_key}"


async def upload_file(db: Session, file: UploadFile) -> FileObject:
    if not file.content_type or not file.content_type.startswith(
        IMAGE_CONTENT_TYPE_PREFIX
    ):
        raise UnsupportedMediaTypeError("이미지 파일만 업로드할 수 있습니다.")

    content = await file.read()

    if len(content) == 0:
        raise ValidationError(
            "입력값을 확인해 주세요.",
            details={"fields": [{"field": "file", "reason": "빈 파일입니다."}]},
        )

    if len(content) > settings.MAX_UPLOAD_BYTES:
        raise FileTooLargeError("파일 크기는 10MB를 초과할 수 없습니다.")

    storage_key = f"{uuid.uuid4().hex}{Path(file.filename or '').suffix}"

    storage_dir = Path(settings.FILE_STORAGE_DIR)
    storage_dir.mkdir(parents=True, exist_ok=True)
    _storage_path(storage_key).write_bytes(content)

    file_object = FileObject(
        storage_key=storage_key,
        original_name=file.filename or storage_key,
        content_type=file.content_type,
        byte_size=len(content),
    )

    return save(db, file_object)
