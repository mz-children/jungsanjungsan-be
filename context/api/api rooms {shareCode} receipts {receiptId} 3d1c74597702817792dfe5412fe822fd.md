# /api/rooms/{shareCode}/receipts/{receiptId}

도메인: receipts
메서드: GET
설명: 결제 내역 상세 조회

```
GET /api/rooms/{roomId}/receipts/{receiptId}
```

## 응답 `200 OK`

```json
{
  "id": "...",
  "merchant": "올레시장",
  "amount": 150000,
  "paidAt": "2025-01-17T18:20:00+09:00",
  "description": "저녁 회식",
  "payer": { "id": "...", "name": "시원" },
  "image": {
    "fileId": "f47ac10b-...",
    "url": "https://cdn.example.com/uploads/2025/01/f47ac10b.jpg"
  },
  "createdAt": "2025-01-17T18:25:00+09:00",
  "updatedAt": "2025-01-17T18:25:00+09:00"
}
```

`description`, `image`는 없으면 null이다.

## 에러

- `404 ROOM_NOT_FOUND`
- `404 RECEIPT_NOT_FOUND` — 소프트 삭제된 경우 포함