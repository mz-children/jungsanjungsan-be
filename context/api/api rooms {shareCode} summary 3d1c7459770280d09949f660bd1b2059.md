# /api/rooms/{shareCode}/summary

도메인: rooms
메서드: GET
설명: 정산방 대시보드 조회

```
GET /api/rooms/{shareCode}/summary
```

정산방 대시보드 화면을 한 번에 조회한다. `room_dashboard_view` + 최근 결제 3건.

## 응답 `200 OK`

```json
{
  "shareCode": "V1StGXR8_Z5j",
  "title": "제주도 여행",
  "status": "ACTIVE",
  "totalBudget": 1000000,
  "totalPaid": 450000,
  "usagePercent": 45.0,
  "memberCount": 3,
  "budgetPerPerson": 333333,
  "receiptCount": 5,
  "createdAt": "2025-01-15T09:00:00+09:00",
  "settledAt": null,
  "recentReceipts": [
    {
      "id": "...",
      "merchant": "올레시장",
      "amount": 150000,
      "paidAt": "2025-01-17T18:20:00+09:00",
      "payer": { "id": "...", "name": "시원" }
    }
  ]
}
```

| 필드 | 설명 |
| --- | --- |
| `usagePercent` | 결제 총액 ÷ 총예산 × 100, 소수 1자리. 예산 0이면 null |
| `budgetPerPerson` | 총예산 ÷ 활성 멤버 수, 버림 |
| `totalPaid` | 소프트 삭제되지 않은 결제 내역의 합계 |
| `recentReceipts` | 최신순 3건. `paid_at DESC, id DESC` |

프로그레스바 5단계 색상은 `usagePercent`로 프론트에서 분기한다.

| 구간 | 상태 |
| --- | --- |
| 25 미만 | 여유 |
| 50 미만 | 정상 |
| 75 미만 | 주의 |
| 100 미만 | 경고 |
| 100 이상 | 초과 |

## 에러

- `404 ROOM_NOT_FOUND`

## 설계 노트 — `usagePercent`가 null일 수 있는 이유

`total_budget`은 0 이상 제약이므로 0이 허용된다. 예산을 정하지 않은 여행이 있을 수 있다. 서버에서 0으로 나누면 예외가 나므로 null을 내려주고, 프론트는 프로그레스바 대신 결제 총액만 표시한다.

0을 내려주면 "예산의 0% 사용 중"이라는 잘못된 문구가 나온다. null은 "계산할 수 없음"이라는 다른 의미다.

## 설계 노트 — LATERAL 조인

멤버 집계와 결제 집계를 각각 서브쿼리로 분리했다. 하나의 JOIN으로 묶으면 카티전 곱이 생겨 합계가 부풀려진다 (DB 모델 문서 4.1).