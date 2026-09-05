# /api/rooms/{shareCode}

도메인: rooms
메서드: GET
설명: 정산방 정보 조회

```
GET /api/rooms/{roomId}
```

공통 헤더의 방 제목, 드로어의 썸네일, 정산방 수정 화면의 폼 초기값에 쓰인다.

## 응답 `200 OK`

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "title": "제주도 여행",
  "totalBudget": 1000000,
  "budgetPerPerson": 333333,
  "thumbnail": {
    "fileId": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "url": "https://cdn.example.com/uploads/2025/01/f47ac10b.jpg"
  },
  "status": "ACTIVE",
  "settledAt": null,
  "createdAt": "2025-01-15T09:00:00+09:00",
  "members": [
    { "id": "...", "name": "시원", "isTreasurer": true,  "displayOrder": 0, "receiptCount": 2 },
    { "id": "...", "name": "동헌", "isTreasurer": false, "displayOrder": 1, "receiptCount": 2 },
    { "id": "...", "name": "지수", "isTreasurer": false, "displayOrder": 2, "receiptCount": 1 }
  ]
}
```

| 필드 | 설명 |
| --- | --- |
| `budgetPerPerson` | 총예산 ÷ 활성 멤버 수, 버림. 저장값이 아닌 파생값 |
| `thumbnail` | 없으면 null |
| `status` | ACTIVE 또는 SETTLED |
| `members` | 활성 멤버만. displayOrder, createdAt 순 정렬 |
| `receiptCount` | 그 멤버 앞으로 살아 있는 결제 건수 |

## 에러

- `404 ROOM_NOT_FOUND`

## 설계 노트 — `receiptCount`를 내려주는 이유

DB 트리거 `guard_member_has_receipts`가 결제 내역이 있는 멤버의 소프트 삭제를 막는다. 이 제약을 프론트가 미리 알아야 정산방 수정 화면에서 삭제 버튼을 비활성화하거나 "결제 내역 2건이 있어 삭제할 수 없습니다"를 띄울 수 있다.

멤버 수가 5~10명 수준이므로 집계 비용은 무시할 만하다.