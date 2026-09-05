import uuid
from datetime import datetime

from pydantic import Field, field_validator

from src.core.schema import CamelModel
from src.files.schema import ThumbnailResponse


def _check_merchant(value: str) -> str:
    if not value.strip():
        raise ValueError("결제처를 입력해 주세요.")
    if len(value) > 100:
        raise ValueError("결제처는 100자 이하여야 합니다.")
    return value


class ReceiptPayerSummary(CamelModel):
    id: uuid.UUID
    name: str


class ReceiptCreateRequest(CamelModel):
    merchant: str
    amount: int = Field(ge=1)
    payer_member_id: uuid.UUID
    paid_at: datetime
    description: str | None = Field(default=None, max_length=500)
    image_file_id: uuid.UUID | None = None

    @field_validator("merchant")
    @classmethod
    def _validate_merchant(cls, value: str) -> str:
        return _check_merchant(value)


class ReceiptPatchRequest(CamelModel):
    merchant: str | None = None
    amount: int | None = Field(default=None, ge=1)
    payer_member_id: uuid.UUID | None = None
    paid_at: datetime | None = None
    description: str | None = Field(default=None, max_length=500)
    image_file_id: uuid.UUID | None = None

    @field_validator("merchant")
    @classmethod
    def _validate_merchant(cls, value: str | None) -> str | None:
        return value if value is None else _check_merchant(value)


class ReceiptResponse(CamelModel):
    id: uuid.UUID
    merchant: str
    amount: int
    paid_at: datetime
    description: str | None
    payer: ReceiptPayerSummary
    image: ThumbnailResponse | None
    created_at: datetime
    updated_at: datetime


class ReceiptListItem(CamelModel):
    id: uuid.UUID
    merchant: str
    amount: int
    paid_at: datetime
    payer: ReceiptPayerSummary


class ReceiptListResponse(CamelModel):
    items: list[ReceiptListItem]
    next_cursor: str | None
    has_next: bool
