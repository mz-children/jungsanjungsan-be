import uuid
from datetime import datetime
from typing import Literal

from src.core.schema import CamelModel

Direction = Literal["RECEIVE", "SEND", "NONE"]
SettlementStatus = Literal["PREVIEW", "SETTLED"]


class SettlementEntryResponse(CamelModel):
    member_id: uuid.UUID | None
    member_name: str
    is_treasurer: bool
    paid_amount: int
    share_amount: int
    balance_amount: int
    direction: Direction


class SettlementResponse(CamelModel):
    status: SettlementStatus
    room_title: str
    period_start_at: datetime
    period_end_at: datetime
    budget_amount: int
    total_amount: int
    budget_diff_percent: float | None
    member_count: int
    per_person_amount: int
    receipt_count: int
    entries: list[SettlementEntryResponse]


class SettlementConfirmRequest(CamelModel):
    expected_total_amount: int | None = None
    expected_receipt_count: int | None = None
