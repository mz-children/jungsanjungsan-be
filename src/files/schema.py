import uuid
from datetime import datetime

from src.core.schema import CamelModel


class FileUploadResponse(CamelModel):
    id: uuid.UUID
    url: str
    original_name: str
    content_type: str
    byte_size: int
    created_at: datetime


class ThumbnailResponse(CamelModel):
    file_id: uuid.UUID
    url: str
