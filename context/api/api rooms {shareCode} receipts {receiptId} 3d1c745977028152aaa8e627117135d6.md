# /api/rooms/{shareCode}/receipts/{receiptId}

도메인: receipts
메서드: DELETE
설명: 결제 내역 삭제 (소프트)

```jsx
DELETE /api/rooms/{shareCode}/receipts/{receiptId}
```

소프트 삭제(`deleted_at`)다. 이후 모든 조회와 집계에서 제외된다.

## 응답

`204 No Content`

## 에러

- `404 ROOM_NOT_FOUND`
- `404 RECEIPT_NOT_FOUND`
- `409 ROOM_ALREADY_SETTLED`

## 설계 노트 — 멱등성을 포기한 이유

이미 삭제된 결제 내역에 다시 요청하면 404다. 멱등하게 204를 주는 방법도 있지만, 여러 명이 같은 방을 편집하는 구조에서는 "누군가 이미 지웠다"는 사실을 알려주는 편이 난다.