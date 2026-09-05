import uuid
from datetime import datetime

from pydantic import Field, field_validator

from src.core.schema import CamelModel
from src.files.schema import ThumbnailResponse
from src.rooms.model import RoomStatus


def _validate_name(value: str, max_length: int, field_name: str) -> str:
    if not value.strip():
        raise ValueError(f"{field_name}을(를) 입력해 주세요.")
    if len(value) > max_length:
        raise ValueError(f"{field_name}은(는) {max_length}자 이하여야 합니다.")
    return value


class MemberCreateInput(CamelModel):
    name: str

    @field_validator("name")
    @classmethod
    def _check_name(cls, value: str) -> str:
        return _validate_name(value, 20, "멤버 이름")


class MemberPatchInput(CamelModel):
    id: uuid.UUID | None = None
    name: str

    @field_validator("name")
    @classmethod
    def _check_name(cls, value: str) -> str:
        return _validate_name(value, 20, "멤버 이름")


class RoomCreateRequest(CamelModel):
    title: str
    total_budget: int = Field(ge=0)
    thumbnail_file_id: uuid.UUID | None = None
    members: list[MemberCreateInput] = Field(min_length=1)

    @field_validator("title")
    @classmethod
    def _check_title(cls, value: str) -> str:
        return _validate_name(value, 50, "정산방 이름")


class RoomPatchRequest(CamelModel):
    title: str | None = None
    total_budget: int | None = Field(default=None, ge=0)
    thumbnail_file_id: uuid.UUID | None = None
    members: list[MemberPatchInput] | None = None

    @field_validator("title")
    @classmethod
    def _check_title(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _validate_name(value, 50, "정산방 이름")


class MemberSummary(CamelModel):
    id: uuid.UUID
    name: str
    is_treasurer: bool
    display_order: int
    receipt_count: int


class RoomResponse(CamelModel):
    # 내부 PK(uuid)는 응답에 노출하지 않는다 (_COMMON.md). 공개 식별자 필드명은
    # "api rooms {shareCode}" 문서에서 shareCode로 확정되었다.
    share_code: str
    title: str
    total_budget: int
    budget_per_person: int
    thumbnail: ThumbnailResponse | None
    status: RoomStatus
    settled_at: datetime | None
    created_at: datetime
    members: list[MemberSummary]


class RoomCreateResponse(RoomResponse):
    """POST /rooms 응답 = 정산방 정보 조회(GET)와 동일한 스키마 + shareUrl."""

    share_url: str


class MembersListResponse(CamelModel):
    members: list[MemberSummary]


class ReceiptPayerSummary(CamelModel):
    id: uuid.UUID
    name: str


class RecentReceiptItem(CamelModel):
    id: uuid.UUID
    merchant: str
    amount: int
    paid_at: datetime
    payer: ReceiptPayerSummary


class RoomSummaryResponse(CamelModel):
    """GET /rooms/{shareCode}/summary. `room_dashboard_view` + 최근 결제 3건.
    썸네일은 이 화면이 아니라 드로어가 GET /rooms/{shareCode}에서 따로 가져온다
    (_COMMON.md 화면별 호출 매핑)."""

    share_code: str
    title: str
    status: RoomStatus
    total_budget: int
    total_paid: int
    usage_percent: float | None
    member_count: int
    budget_per_person: int
    receipt_count: int
    created_at: datetime
    settled_at: datetime | None
    recent_receipts: list[RecentReceiptItem]
