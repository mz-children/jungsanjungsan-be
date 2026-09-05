"""_COMMON.md 공통 에러 규약. 모든 API 에러는
`{"error": {"code", "message", "details"}}` 형태로 내려간다 (main.py의 예외 핸들러 참고)."""

from typing import Any


class AppError(Exception):
    status_code: int = 400
    code: str = "APPLICATION_ERROR"

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        self.message = message
        self.details = details
        super().__init__(message)


class ValidationError(AppError):
    status_code = 400
    code = "VALIDATION_ERROR"


class InvalidPayerError(AppError):
    status_code = 400
    code = "INVALID_PAYER"


class NoActiveMemberError(AppError):
    status_code = 400
    code = "NO_ACTIVE_MEMBER"


class RoomNotFoundError(AppError):
    status_code = 404
    code = "ROOM_NOT_FOUND"


class ReceiptNotFoundError(AppError):
    status_code = 404
    code = "RECEIPT_NOT_FOUND"


class SettlementNotFoundError(AppError):
    status_code = 404
    code = "SETTLEMENT_NOT_FOUND"


class RoomAlreadySettledError(AppError):
    status_code = 409
    code = "ROOM_ALREADY_SETTLED"


class DuplicateMemberNameError(AppError):
    status_code = 409
    code = "DUPLICATE_MEMBER_NAME"


class MemberHasReceiptsError(AppError):
    status_code = 409
    code = "MEMBER_HAS_RECEIPTS"


class SettlementStaleError(AppError):
    status_code = 409
    code = "SETTLEMENT_STALE"


class FileTooLargeError(AppError):
    status_code = 413
    code = "FILE_TOO_LARGE"


class UnsupportedMediaTypeError(AppError):
    status_code = 415
    code = "UNSUPPORTED_MEDIA_TYPE"


class InternalError(AppError):
    """DB_MODEL.md 6.2 — `sum(balanceAmount) = 0` 불변식은 행 간 집계라 CHECK로
    표현할 수 없다. 응답 직전 애플리케이션에서 검증하고, 어긋나면 500으로 실패해야 한다."""

    status_code = 500
    code = "INTERNAL_ERROR"
