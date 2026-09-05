import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.receipts import service
from src.receipts.schema import (
    ReceiptCreateRequest,
    ReceiptListResponse,
    ReceiptPatchRequest,
    ReceiptResponse,
)

router = APIRouter(prefix="/rooms/{share_code}/receipts", tags=["receipts"])


@router.post("", response_model=ReceiptResponse, status_code=201)
def create_receipt(
    share_code: str,
    data: ReceiptCreateRequest,
    db: Session = Depends(get_db),
):
    return service.create_receipt(db, share_code, data)


@router.get("", response_model=ReceiptListResponse)
def list_receipts(
    share_code: str,
    q: str | None = None,
    payer_member_id: uuid.UUID | None = Query(default=None, alias="payerMemberId"),
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return service.list_receipts(
        db,
        share_code,
        q=q,
        payer_member_id=payer_member_id,
        cursor=cursor,
        limit=limit,
    )


@router.get("/{receipt_id}", response_model=ReceiptResponse)
def get_receipt(
    share_code: str,
    receipt_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    return service.get_receipt(db, share_code, receipt_id)


@router.patch("/{receipt_id}", response_model=ReceiptResponse)
def update_receipt(
    share_code: str,
    receipt_id: uuid.UUID,
    data: ReceiptPatchRequest,
    db: Session = Depends(get_db),
):
    return service.update_receipt(db, share_code, receipt_id, data)


@router.delete("/{receipt_id}", status_code=204)
def delete_receipt(
    share_code: str,
    receipt_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    service.delete_receipt(db, share_code, receipt_id)
