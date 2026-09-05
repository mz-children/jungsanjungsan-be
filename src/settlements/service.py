import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.errors import (
    InternalError,
    NoActiveMemberError,
    RoomAlreadySettledError,
    SettlementNotFoundError,
    SettlementStaleError,
)
from src.members import repository as member_repo
from src.members.model import Member
from src.receipts import repository as receipt_repo
from src.rooms.model import Room, RoomStatus
from src.rooms.service import get_room_or_404
from src.settlements import repository as settlement_repo
from src.settlements.model import Settlement, SettlementEntry
from src.settlements.schema import (
    Direction,
    SettlementConfirmRequest,
    SettlementEntryResponse,
    SettlementResponse,
)

_DIRECTION_ORDER = {"RECEIVE": 0, "SEND": 1, "NONE": 2}


def _direction(balance_amount: int) -> Direction:
    if balance_amount > 0:
        return "RECEIVE"
    if balance_amount < 0:
        return "SEND"
    return "NONE"


def _budget_diff_percent(total_amount: int, budget_amount: int) -> float | None:
    if budget_amount == 0:
        return None
    return round((total_amount - budget_amount) / budget_amount * 100, 1)


def _calculate_entries(
    members: list[Member],
    paid_by_member: dict[uuid.UUID, int],
    total_amount: int,
) -> list[dict]:
    """DB_MODEL.md 6.2 — 나머지는 총무의 shareAmount에 몰아준다.
    `sum(balanceAmount) = 0`은 행 간 집계라 CHECK로 표현할 수 없으므로 여기서 검증한다."""

    member_count = len(members)
    if member_count == 0:
        raise NoActiveMemberError("정산할 활성 멤버가 없습니다.")

    base_share, remainder = divmod(total_amount, member_count)
    treasurer = next((m for m in members if m.is_treasurer), members[0])

    entries = []
    for member in members:
        share_amount = (
            base_share + remainder if member.id == treasurer.id else base_share
        )
        paid_amount = paid_by_member.get(member.id, 0)
        entries.append(
            {
                "member": member,
                "paid_amount": paid_amount,
                "share_amount": share_amount,
                "balance_amount": paid_amount - share_amount,
            }
        )

    if sum(e["balance_amount"] for e in entries) != 0:
        raise InternalError("정산 잔액 합계가 0이 아닙니다.")

    return entries


def _sort_entries(entries: list[dict]) -> list[dict]:
    return sorted(
        entries,
        key=lambda e: (
            _DIRECTION_ORDER[_direction(e["balance_amount"])],
            -abs(e["balance_amount"]),
        ),
    )


def _entry_responses(entries: list[dict]) -> list[SettlementEntryResponse]:
    return [
        SettlementEntryResponse(
            member_id=e["member"].id,
            member_name=e["member"].name,
            is_treasurer=e["member"].is_treasurer,
            paid_amount=e["paid_amount"],
            share_amount=e["share_amount"],
            balance_amount=e["balance_amount"],
            direction=_direction(e["balance_amount"]),
        )
        for e in entries
    ]


def preview_settlement(db: Session, share_code: str) -> SettlementResponse:
    room = get_room_or_404(db, share_code)
    if room.status == RoomStatus.SETTLED:
        raise RoomAlreadySettledError("이미 정산이 완료된 방입니다.")

    members = member_repo.list_by_room(db, room.id)
    total_amount, receipt_count = receipt_repo.aggregate_active_by_room(db, room.id)
    paid_by_member = receipt_repo.sum_active_amount_by_payer(db, room.id)

    entries = _sort_entries(_calculate_entries(members, paid_by_member, total_amount))

    return SettlementResponse(
        status="PREVIEW",
        room_title=room.title,
        period_start_at=room.created_at,
        period_end_at=datetime.now(timezone.utc),
        budget_amount=room.total_budget,
        total_amount=total_amount,
        budget_diff_percent=_budget_diff_percent(total_amount, room.total_budget),
        member_count=len(members),
        per_person_amount=total_amount // len(members),
        receipt_count=receipt_count,
        entries=_entry_responses(entries),
    )


def confirm_settlement(
    db: Session, share_code: str, data: SettlementConfirmRequest
) -> SettlementResponse:
    """DB_MODEL.md 5.2 — 방을 잠그고 상태 확인 → 스냅샷 생성 → 방 상태 전환(반드시 마지막)."""

    room = get_room_or_404(db, share_code)

    locked_id = db.execute(
        select(Room.id)
        .where(Room.id == room.id, Room.status == RoomStatus.ACTIVE)
        .with_for_update()
    ).scalar_one_or_none()
    if locked_id is None:
        db.rollback()
        raise RoomAlreadySettledError("이미 정산이 완료된 방입니다.")

    members = member_repo.list_by_room(db, room.id)
    total_amount, receipt_count = receipt_repo.aggregate_active_by_room(db, room.id)

    if data.expected_total_amount is not None or data.expected_receipt_count is not None:
        expected_total = (
            data.expected_total_amount
            if data.expected_total_amount is not None
            else total_amount
        )
        expected_count = (
            data.expected_receipt_count
            if data.expected_receipt_count is not None
            else receipt_count
        )
        if expected_total != total_amount or expected_count != receipt_count:
            db.rollback()
            raise SettlementStaleError(
                "미리보기 이후 결제 내역이 변경되었습니다.",
                details={
                    "expected": {
                        "totalAmount": expected_total,
                        "receiptCount": expected_count,
                    },
                    "actual": {
                        "totalAmount": total_amount,
                        "receiptCount": receipt_count,
                    },
                },
            )

    paid_by_member = receipt_repo.sum_active_amount_by_payer(db, room.id)
    entries = _calculate_entries(members, paid_by_member, total_amount)

    period_end_at = datetime.now(timezone.utc)
    settlement = Settlement(
        room_id=room.id,
        room_title=room.title,
        budget_amount=room.total_budget,
        period_start_at=room.created_at,
        period_end_at=period_end_at,
        total_amount=total_amount,
        member_count=len(members),
        per_person_amount=total_amount // len(members),
        receipt_count=receipt_count,
    )
    db.add(settlement)
    db.flush()

    db.add_all(
        SettlementEntry(
            settlement_id=settlement.id,
            member_id=e["member"].id,
            member_name=e["member"].name,
            is_treasurer=e["member"].is_treasurer,
            paid_amount=e["paid_amount"],
            share_amount=e["share_amount"],
        )
        for e in entries
    )

    # guard_room_settled 트리거 때문에 방 상태 전환은 반드시 마지막이다.
    room.status = RoomStatus.SETTLED
    room.settled_at = period_end_at

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise RoomAlreadySettledError("이미 정산이 완료된 방입니다.") from exc

    return SettlementResponse(
        status="SETTLED",
        room_title=settlement.room_title,
        period_start_at=settlement.period_start_at,
        period_end_at=settlement.period_end_at,
        budget_amount=settlement.budget_amount,
        total_amount=settlement.total_amount,
        budget_diff_percent=_budget_diff_percent(
            settlement.total_amount, settlement.budget_amount
        ),
        member_count=settlement.member_count,
        per_person_amount=settlement.per_person_amount,
        receipt_count=settlement.receipt_count,
        entries=_entry_responses(_sort_entries(entries)),
    )


def get_settlement(db: Session, share_code: str) -> SettlementResponse:
    room = get_room_or_404(db, share_code)
    settlement = settlement_repo.find_by_room_id(db, room.id)
    if settlement is None:
        raise SettlementNotFoundError("확정된 정산 결과가 없습니다.")

    rows = settlement_repo.list_entries_by_settlement(db, settlement.id)
    sorted_rows = sorted(
        rows,
        key=lambda row: (
            _DIRECTION_ORDER[_direction(row.balance_amount)],
            -abs(row.balance_amount),
        ),
    )

    return SettlementResponse(
        status="SETTLED",
        room_title=settlement.room_title,
        period_start_at=settlement.period_start_at,
        period_end_at=settlement.period_end_at,
        budget_amount=settlement.budget_amount,
        total_amount=settlement.total_amount,
        budget_diff_percent=_budget_diff_percent(
            settlement.total_amount, settlement.budget_amount
        ),
        member_count=settlement.member_count,
        per_person_amount=settlement.per_person_amount,
        receipt_count=settlement.receipt_count,
        entries=[
            SettlementEntryResponse(
                member_id=row.member_id,
                member_name=row.member_name,
                is_treasurer=row.is_treasurer,
                paid_amount=row.paid_amount,
                share_amount=row.share_amount,
                balance_amount=row.balance_amount,
                direction=_direction(row.balance_amount),
            )
            for row in sorted_rows
        ],
    )
