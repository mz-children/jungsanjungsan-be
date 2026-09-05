from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from src.config import settings
from src.core.errors import AppError
from src.files.router import router as files_router
from src.receipts.router import router as receipts_router
from src.rooms.router import router as rooms_router
from src.settlements.router import router as settlements_router
from src.users.router import user

app = FastAPI()


@app.exception_handler(AppError)
def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


@app.exception_handler(RequestValidationError)
def handle_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    # _COMMON.md 공통 에러 규약: VALIDATION_ERROR의 details는 필드 단위 배열이다.
    # pydantic은 커스텀 validator의 ValueError 메시지 앞에 "Value error, "를 붙이므로 제거한다.
    fields = [
        {
            "field": ".".join(str(part) for part in error["loc"][1:]),
            "reason": error["msg"].removeprefix("Value error, "),
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "입력값을 확인해 주세요.",
                "details": {"fields": fields},
            }
        },
    )


@app.get("/")
def read_root():
    return {"Hello": "DH!"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}


app.include_router(user)

app.include_router(rooms_router, prefix="/api")
app.include_router(files_router, prefix="/api")
app.include_router(receipts_router, prefix="/api")
app.include_router(settlements_router, prefix="/api")

Path(settings.FILE_STORAGE_DIR).mkdir(parents=True, exist_ok=True)
app.mount(
    "/uploads", StaticFiles(directory=settings.FILE_STORAGE_DIR), name="uploads"
)
