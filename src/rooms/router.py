from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.rooms import service
from src.rooms.schema import (
    MembersListResponse,
    RoomCreateRequest,
    RoomCreateResponse,
    RoomPatchRequest,
    RoomResponse,
    RoomSummaryResponse,
)

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.post("", response_model=RoomCreateResponse, status_code=201)
def create_room(
    data: RoomCreateRequest,
    db: Session = Depends(get_db),
):
    return service.create_room(db, data)


@router.get("/{share_code}", response_model=RoomResponse)
def get_room(
    share_code: str,
    db: Session = Depends(get_db),
):
    return service.get_room(db, share_code)


@router.patch("/{share_code}", response_model=RoomResponse)
def update_room(
    share_code: str,
    data: RoomPatchRequest,
    db: Session = Depends(get_db),
):
    return service.update_room(db, share_code, data)


@router.get("/{share_code}/summary", response_model=RoomSummaryResponse)
def get_summary(
    share_code: str,
    db: Session = Depends(get_db),
):
    return service.get_summary(db, share_code)


@router.get("/{share_code}/members", response_model=MembersListResponse)
def get_members(
    share_code: str,
    db: Session = Depends(get_db),
):
    return service.get_members(db, share_code)
