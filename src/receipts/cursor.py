import base64
import uuid
from datetime import datetime

from src.core.errors import ValidationError


def encode_cursor(paid_at: datetime, receipt_id: uuid.UUID) -> str:
    raw = f"{paid_at.isoformat()}|{receipt_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode(padded.encode()).decode()
        paid_at_raw, receipt_id_raw = raw.split("|")
        return datetime.fromisoformat(paid_at_raw), uuid.UUID(receipt_id_raw)
    except Exception as exc:
        raise ValidationError(
            "입력값을 확인해 주세요.",
            details={
                "fields": [{"field": "cursor", "reason": "유효하지 않은 커서입니다."}]
            },
        ) from exc
