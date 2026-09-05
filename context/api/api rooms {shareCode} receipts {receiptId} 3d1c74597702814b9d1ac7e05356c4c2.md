# /api/rooms/{shareCode}/receipts/{receiptId}

도메인: receipts
메서드: PATCH
설명: 결제 내역 수정

```
PATCH /api/rooms/{roomId}/receipts/{receiptId}
```

## 요청

생성과 동일한 필드, 전부 선택. 상위 페이지의 null 처리 규칙을 따른다.

```json
{
  "amount": 155000,
  "description": null
}
```

키가 존재하는 필드만 수정한다. `description`과 `imageFileId`를 비우려면 명시적으로 null을 보낸다.

## 응답 `200 OK`

결제 내역 상세 조회와 동일한 스키마.

## 에러

- `400 VALIDATION_ERROR`
- `400 INVALID_PAYER`
- `404 ROOM_NOT_FOUND`
- `404 RECEIPT_NOT_FOUND`
- `409 ROOM_ALREADY_SETTLED`