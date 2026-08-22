from sqlalchemy.orm import Session

from src.users.schema import UserCreate
from src.users.repository import get_all_user, find_by_email, save
from src.users.model import User


def get_user_list(
    db: Session,
) -> list[User]:

    return get_all_user(db)


def create_user(
    db: Session,
    data: UserCreate,
) -> User:

    existing_user = find_by_email(db, data.email)

    if existing_user:
        raise ValueError("이미 존재하는 이메일입니다.")

    user = User(
        name=data.name,
        email=data.email,
    )

    return save(db, user)
