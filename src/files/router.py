from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.files import service
from src.files.schema import FileUploadResponse

router = APIRouter(prefix="/files", tags=["files"])


@router.post("", response_model=FileUploadResponse, status_code=201)
async def upload(
    file: UploadFile,
    db: Session = Depends(get_db),
):
    file_object = await service.upload_file(db, file)

    return FileUploadResponse(
        id=file_object.id,
        url=service.to_url(file_object),
        original_name=file_object.original_name,
        content_type=file_object.content_type,
        byte_size=file_object.byte_size,
        created_at=file_object.created_at,
    )
