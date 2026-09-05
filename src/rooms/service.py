import uuid
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.config import settings
from src.core.errors import (
    DuplicateMemberNameError,
    MemberHasReceiptsError,
    RoomAlreadySettledError,
    RoomNotFoundError,
    ValidationError,
)
from src.files import repository as file_repo
from src.files import service as file_service
from src.files.schema import ThumbnailResponse
from src.members import repository as member_repo
from src.members.model import Member
from src.receipts import repository as receipt_repo
from src.rooms import repository as room_repo
from src.rooms.model import Room, RoomStatus
from src.rooms.schema import (
    MemberPatchInput,
    MemberSummary,
    ReceiptPayerSummary,
    RecentReceiptItem,
    RoomCreateRequest,
    RoomCreateResponse,
    RoomPatchRequest,
    RoomResponse,
    MembersListResponse,
    RoomSummaryResponse,
)
from src.rooms.share_code import generate_share_code


def _normalize_name(name: str) -> str:
    return name.strip().lower()


def _ensure_no_duplicate_names(names: list[str]) -> None:
    seen: set[str] = set()
    for name in names:
        normalized = _normalize_name(name)
        if normalized in seen:
            raise DuplicateMemberNameError(
                "정산방 내 멤버 이름은 중복될 수 없습니다.",
                details={
                    "fields": [
                        {
                            "field": "members",
                            "reason": f"'{name.strip()}' 이름이 중복되었습니다.",
                        }
                    ]
                },
            )
        seen.add(normalized)


def _ensure_file_exists(db: Session, file_id: uuid.UUID, field: str) -> None:
    if file_repo.get_by_id(db, file_id) is None:
        raise ValidationError(
            "입력값을 확인해 주세요.",
            details={
                "fields": [{"field": field, "reason": "존재하지 않는 파일입니다."}]
            },
        )


def get_room_or_404(db: Session, share_code: str) -> Room:
    room = room_repo.find_by_share_code(db, share_code)
    if room is None:
        raise RoomNotFoundError(
            "정산방을 찾을 수 없습니다.", details={"shareCode": share_code}
        )
    return room


def _to_thumbnail(db: Session, thumbnail_file_id: uuid.UUID | None) -> ThumbnailResponse | None:
    if thumbnail_file_id is None:
        return None
    file_object = file_repo.get_by_id(db, thumbnail_file_id)
    if file_object is None:
        return None
    return ThumbnailResponse(file_id=file_object.id, url=file_service.to_url(file_object))


def _build_room_response(db: Session, room: Room) -> RoomResponse:
    members = member_repo.list_by_room(db, room.id)
    receipt_counts = receipt_repo.count_active_by_payer(db, room.id)
    member_count = len(members)

    return RoomResponse(
        share_code=room.share_code,
        title=room.title,
        total_budget=room.total_budget,
        budget_per_person=room.total_budget // member_count if member_count else 0,
        thumbnail=_to_thumbnail(db, room.thumbnail_file_id),
        status=room.status,
        settled_at=room.settled_at,
        created_at=room.created_at,
        members=[
            MemberSummary(
                id=m.id,
                name=m.name,
                is_treasurer=m.is_treasurer,
                display_order=m.display_order,
                receipt_count=receipt_counts.get(m.id, 0),
            )
            for m in members
        ],
    )


def create_room(db: Session, data: RoomCreateRequest) -> RoomCreateResponse:
    _ensure_no_duplicate_names([m.name for m in data.members])

    if data.thumbnail_file_id is not None:
        _ensure_file_exists(db, data.thumbnail_file_id, "thumbnailFileId")

    room = Room(title=data.title, total_budget=data.total_budget)
    room.thumbnail_file_id = data.thumbnail_file_id

    last_error: IntegrityError | None = None
    for _ in range(3):
        room.share_code = generate_share_code()
        try:
            db.add(room)
            db.flush()
            last_error = None
            break
        except IntegrityError as exc:
            db.rollback()
            last_error = exc
    if last_error is not None:
        raise last_error

    members = [
        Member(
            room_id=room.id,
            name=member.name,
            is_treasurer=(index == 0),
            display_order=index,
        )
        for index, member in enumerate(data.members)
    ]
    db.add_all(members)
    db.commit()
    db.refresh(room)

    room_response = _build_room_response(db, room)
    share_url = f"{settings.FRONTEND_BASE_URL}/room/{room.share_code}"

    return RoomCreateResponse(**room_response.model_dump(), share_url=share_url)


def get_room(db: Session, share_code: str) -> RoomResponse:
    room = get_room_or_404(db, share_code)
    return _build_room_response(db, room)


def get_members(db: Session, share_code: str) -> MembersListResponse:
    room = get_room_or_404(db, share_code)
    members = member_repo.list_by_room(db, room.id)
    receipt_counts = receipt_repo.count_active_by_payer(db, room.id)

    return MembersListResponse(
        members=[
            MemberSummary(
                id=m.id,
                name=m.name,
                is_treasurer=m.is_treasurer,
                display_order=m.display_order,
                receipt_count=receipt_counts.get(m.id, 0),
            )
            for m in members
        ]
    )


def _sync_members(db: Session, room: Room, inputs: list[MemberPatchInput]) -> None:
    """`members` 배열은 선언적 동기화다: id 있으면 갱신, 없으면 신규, 배열에서
    빠지면 소프트 삭제 (api rooms {shareCode} PATCH 문서)."""

    _ensure_no_duplicate_names([m.name for m in inputs])

    existing_members = {m.id: m for m in member_repo.list_by_room(db, room.id)}
    incoming_ids = {m.id for m in inputs if m.id is not None}

    unknown_ids = incoming_ids - existing_members.keys()
    if unknown_ids:
        raise ValidationError(
            "입력값을 확인해 주세요.",
            details={
                "fields": [
                    {"field": "members", "reason": "존재하지 않는 멤버 id가 포함되어 있습니다."}
                ]
            },
        )

    removed_ids = existing_members.keys() - incoming_ids
    receipt_counts = receipt_repo.count_active_by_payer(db, room.id)
    blocked = [
        {
            "id": str(member_id),
            "name": existing_members[member_id].name,
            "receiptCount": receipt_counts[member_id],
        }
        for member_id in removed_ids
        if receipt_counts.get(member_id, 0) > 0
    ]
    if blocked:
        raise MemberHasReceiptsError(
            "결제 내역이 있는 멤버는 삭제할 수 없습니다.", details={"members": blocked}
        )

    for member_id in removed_ids:
        existing_members[member_id].deleted_at = datetime.now(timezone.utc)

    for index, member_input in enumerate(inputs):
        if member_input.id is not None:
            member = existing_members[member_input.id]
            member.name = member_input.name
            member.display_order = index
        else:
            db.add(
                Member(
                    room_id=room.id,
                    name=member_input.name,
                    display_order=index,
                    is_treasurer=False,
                )
            )


def update_room(db: Session, share_code: str, patch: RoomPatchRequest) -> RoomResponse:
    room = get_room_or_404(db, share_code)
    if room.status == RoomStatus.SETTLED:
        raise RoomAlreadySettledError("정산이 완료된 방은 수정할 수 없습니다.")

    patch_fields = patch.model_dump(exclude_unset=True)

    if "title" in patch_fields:
        room.title = patch.title
    if "total_budget" in patch_fields:
        room.total_budget = patch.total_budget
    if "thumbnail_file_id" in patch_fields:
        if patch.thumbnail_file_id is not None:
            _ensure_file_exists(db, patch.thumbnail_file_id, "thumbnailFileId")
        room.thumbnail_file_id = patch.thumbnail_file_id
    if patch.members is not None:
        _sync_members(db, room, patch.members)

    db.commit()
    db.refresh(room)

    return _build_room_response(db, room)


def get_summary(db: Session, share_code: str) -> RoomSummaryResponse:
    room = get_room_or_404(db, share_code)

    row = db.execute(
        text("SELECT * FROM room_dashboard_view WHERE room_id = :room_id"),
        {"room_id": room.id},
    ).mappings().first()

    members_by_id = {m.id: m for m in member_repo.list_by_room(db, room.id)}
    recent_receipts = receipt_repo.list_by_room(db, room.id, limit=3)

    return RoomSummaryResponse(
        share_code=room.share_code,
        title=row["title"],
        status=row["status"],
        total_budget=row["total_budget"],
        total_paid=row["total_paid"],
        usage_percent=(
            float(row["usage_percent"]) if row["usage_percent"] is not None else None
        ),
        member_count=row["member_count"],
        budget_per_person=row["budget_per_person"],
        receipt_count=row["receipt_count"],
        created_at=row["created_at"],
        settled_at=row["settled_at"],
        recent_receipts=[
            RecentReceiptItem(
                id=r.id,
                merchant=r.merchant,
                amount=r.amount,
                paid_at=r.paid_at,
                payer=ReceiptPayerSummary(
                    id=r.payer_member_id,
                    name=members_by_id[r.payer_member_id].name,
                ),
            )
            for r in recent_receipts
        ],
    )
