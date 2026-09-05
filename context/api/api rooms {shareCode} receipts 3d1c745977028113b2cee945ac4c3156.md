# /api/rooms/{shareCode}/receipts

도메인: receipts
메서드: POST
설명: 결제 내역 생성

```jsx
POST /api/rooms/{shareCode}/receipts
```

## 요청

```json
{
  "merchant": "올레시장",
  "amount": 150000,
  "payerMemberId": "a1b2c3d4-...",
  "paidAt": "2025-01-17T18:20:00+09:00",
  "description": "저녁 회식",
  "imageFileId": "f47ac10b-..."
}
```

| 필드 | 타입 | 필수 | 검증 |
| --- | --- | --- | --- |
| `merchant` | string | Y | 공백 제외 1자 이상, 100자 이하 |
| `amount` | integer | Y | 1 이상 (0원 결제 불가) |
| `payerMemberId` | uuid | Y | 이 방의 활성 멤버 |
| `paidAt` | timestamp | Y | — |
| `description` | string | N | 500자 이하 |
| `imageFileId` | uuid | N | 존재하는 `file_object.id` |

## 응답 `201 Created`

결제 내역 상세 조회와 동일한 스키마.

## 에러

- `400 VALIDATION_ERROR`
- `400 INVALID_PAYER`
- `404 ROOM_NOT_FOUND`
- `409 ROOM_ALREADY_SETTLED`

## 설계 노트 — `INVALID_PAYER`

DB의 복합 FK `receipt_payer_fk (room_id, payer_member_id)`가 다른 방 멤버를 결제자로 지정하는 것을 막는다. 하지만 FK 위반이 그대로 올라오면 에러 코드 23503뿐이라 프론트가 안내 문구를 만들 수 없다.

애플리케이션에서 먼저 확인하고 `400 INVALID_PAYER`를 반환한다. DB 제약은 경합 상황(멤버가 방금 삭제된 경우)의 최종 방어선으로 남는다.