from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.settlements import service
from src.settlements.schema import SettlementConfirmRequest, SettlementResponse

router = APIRouter(prefix="/rooms/{share_code}/settlement", tags=["settlement"])


@router.get("/preview", response_model=SettlementResponse)
def preview_settlement(
    share_code: str,
    db: Session = Depends(get_db),
):
    return service.preview_settlement(db, share_code)


@router.post("", response_model=SettlementResponse, status_code=201)
def confirm_settlement(
    share_code: str,
    data: SettlementConfirmRequest,
    db: Session = Depends(get_db),
):
    return service.confirm_settlement(db, share_code, data)


@router.get("", response_model=SettlementResponse)
def get_settlement(
    share_code: str,
    db: Session = Depends(get_db),
):
    return service.get_settlement(db, share_code)
