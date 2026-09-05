import uuid

from sqlalchemy.orm import Session

from src.core.errors import (
    InvalidPayerError,
    ReceiptNotFoundError,
    RoomAlreadySettledError,
    ValidationError,
)
from src.files import repository as file_repo
from src.files import service as file_service
from src.files.schema import ThumbnailResponse
from src.members import repository as member_repo
from src.members.model import Member
from src.receipts import repository as receipt_repo
from src.receipts.cursor import decode_cursor, encode_cursor
from src.receipts.model import Receipt
from src.receipts.schema import (
    ReceiptCreateRequest,
    ReceiptListItem,
    ReceiptListResponse,
    ReceiptPatchRequest,
    ReceiptPayerSummary,
    ReceiptResponse,
)
from src.rooms.model import Room, RoomStatus
from src.rooms.service import get_room_or_404


def _ensure_writable(room: Room) -> None:
    if room.status == RoomStatus.SETTLED:
        raise RoomAlreadySettledError("정산이 완료된 방은 수정할 수 없습니다.")


def _ensure_valid_payer(db: Session, room_id: uuid.UUID, payer_member_id: uuid.UUID) -> Member:
    payer = member_repo.get_active_in_room(db, room_id, payer_member_id)
    if payer is None:
        raise InvalidPayerError("결제자는 이 방의 활성 멤버여야 합니다.")
    return payer


def _ensure_file_exists(db: Session, file_id: uuid.UUID, field: str) -> None:
    if file_repo.get_by_id(db, file_id) is None:
        raise ValidationError(
            "입력값을 확인해 주세요.",
            details={
                "fields": [{"field": field, "reason": "존재하지 않는 파일입니다."}]
            },
        )


def _get_receipt_or_404(
    db: Session, room_id: uuid.UUID, receipt_id: uuid.UUID
) -> Receipt:
    receipt = receipt_repo.find_by_id_in_room(db, room_id, receipt_id)
    if receipt is None:
        raise ReceiptNotFoundError("결제 내역을 찾을 수 없습니다.")
    return receipt


def _build_response(db: Session, receipt: Receipt, payer: Member) -> ReceiptResponse:
    image = None
    if receipt.image_file_id is not None:
        file_object = file_repo.get_by_id(db, receipt.image_file_id)
        if file_object is not None:
            image = ThumbnailResponse(
                file_id=file_object.id, url=file_service.to_url(file_object)
            )

    return ReceiptResponse(
        id=receipt.id,
        merchant=receipt.merchant,
        amount=receipt.amount,
        paid_at=receipt.paid_at,
        description=receipt.description,
        payer=ReceiptPayerSummary(id=payer.id, name=payer.name),
        image=image,
        created_at=receipt.created_at,
        updated_at=receipt.updated_at,
    )


def create_receipt(
    db: Session, share_code: str, data: ReceiptCreateRequest
) -> ReceiptResponse:
    room = get_room_or_404(db, share_code)
    _ensure_writable(room)
    payer = _ensure_valid_payer(db, room.id, data.payer_member_id)

    if data.image_file_id is not None:
        _ensure_file_exists(db, data.image_file_id, "imageFileId")

    receipt = Receipt(
        room_id=room.id,
        payer_member_id=data.payer_member_id,
        merchant=data.merchant,
        amount=data.amount,
        paid_at=data.paid_at,
        description=data.description,
        image_file_id=data.image_file_id,
    )
    receipt_repo.save(db, receipt)

    return _build_response(db, receipt, payer)


def get_receipt(db: Session, share_code: str, receipt_id: uuid.UUID) -> ReceiptResponse:
    room = get_room_or_404(db, share_code)
    receipt = _get_receipt_or_404(db, room.id, receipt_id)
    payer = member_repo.get_by_id(db, receipt.payer_member_id)

    return _build_response(db, receipt, payer)


def list_receipts(
    db: Session,
    share_code: str,
    *,
    q: str | None,
    payer_member_id: uuid.UUID | None,
    cursor: str | None,
    limit: int,
) -> ReceiptListResponse:
    room = get_room_or_404(db, share_code)
    decoded_cursor = decode_cursor(cursor) if cursor else None

    # 다음 페이지 존재 여부를 알기 위해 limit보다 1건 더 조회한다.
    receipts = receipt_repo.list_by_room_cursor(
        db,
        room.id,
        payer_member_id=payer_member_id,
        q=q,
        cursor=decoded_cursor,
        limit=limit + 1,
    )

    has_next = len(receipts) > limit
    page = receipts[:limit]

    payers = {m.id: m for m in member_repo.list_by_room(db, room.id)}

    next_cursor = None
    if has_next and page:
        last = page[-1]
        next_cursor = encode_cursor(last.paid_at, last.id)

    return ReceiptListResponse(
        items=[
            ReceiptListItem(
                id=r.id,
                merchant=r.merchant,
                amount=r.amount,
                paid_at=r.paid_at,
                payer=ReceiptPayerSummary(
                    id=r.payer_member_id, name=payers[r.payer_member_id].name
                ),
            )
            for r in page
        ],
        next_cursor=next_cursor,
        has_next=has_next,
    )


def update_receipt(
    db: Session, share_code: str, receipt_id: uuid.UUID, patch: ReceiptPatchRequest
) -> ReceiptResponse:
    room = get_room_or_404(db, share_code)
    _ensure_writable(room)
    receipt = _get_receipt_or_404(db, room.id, receipt_id)

    patch_fields = patch.model_dump(exclude_unset=True)

    if "merchant" in patch_fields:
        receipt.merchant = patch.merchant
    if "amount" in patch_fields:
        receipt.amount = patch.amount
    if "payer_member_id" in patch_fields:
        _ensure_valid_payer(db, room.id, patch.payer_member_id)
        receipt.payer_member_id = patch.payer_member_id
    if "paid_at" in patch_fields:
        receipt.paid_at = patch.paid_at
    if "description" in patch_fields:
        receipt.description = patch.description
    if "image_file_id" in patch_fields:
        if patch.image_file_id is not None:
            _ensure_file_exists(db, patch.image_file_id, "imageFileId")
        receipt.image_file_id = patch.image_file_id

    db.commit()
    db.refresh(receipt)

    payer = member_repo.get_by_id(db, receipt.payer_member_id)
    return _build_response(db, receipt, payer)


def delete_receipt(db: Session, share_code: str, receipt_id: uuid.UUID) -> None:
    room = get_room_or_404(db, share_code)
    _ensure_writable(room)
    receipt = _get_receipt_or_404(db, room.id, receipt_id)
    receipt_repo.soft_delete(db, receipt)
