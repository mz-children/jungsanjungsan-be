import uuid

from sqlalchemy.orm import Session

from src.files.model import FileObject


def get_by_id(
    db: Session,
    file_id: uuid.UUID,
) -> FileObject | None:
    return db.get(FileObject, file_id)


def save(
    db: Session,
    file_object: FileObject,
) -> FileObject:
    db.add(file_object)
    db.commit()
    db.refresh(file_object)

    return file_object


def delete(
    db: Session,
    file_object: FileObject,
) -> None:
    db.delete(file_object)
    db.commit()
