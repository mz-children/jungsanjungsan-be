from sqlalchemy import select
from sqlalchemy.orm import Session

from src.users.model import User


def get_all_user(db: Session) -> list[User]:
    return db.scalars(select(User)).all()


def find_by_email(
    db: Session,
    email: str,
) -> User | None:
    return db.query(User).filter(User.email == email).first()


def save(
    db: Session,
    user: User,
) -> User:
    db.add(user)
    db.commit()
    db.refresh(user)

    return user
