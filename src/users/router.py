from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.users.schema import UserCreate, UserResponse
from src.users.service import get_user_list, create_user

user = APIRouter(prefix="/users", tags=["users"])


@user.get("", response_model=list[UserResponse])
def getList(
    db: Session = Depends(get_db),
):
    return get_user_list(db)


@user.post("", response_model=UserResponse)
def create(
    data: UserCreate,
    db: Session = Depends(get_db),
):
    return create_user(db, data)
