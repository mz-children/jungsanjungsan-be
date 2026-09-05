# /api/rooms/{shareCode}/settlement/preview

도메인: settlement
메서드: GET
설명: 정산 미리보기 (저장 안 함)

```
GET /api/rooms/{roomId}/settlement/preview
```

계산만 하고 저장하지 않는다. 여러 번 호출해도 부작용이 없다.

피그마상 정산 완료는 두 단계다. 드로어의 "정산 완료하기" → 확인 모달 → 정산 결과 화면 이동(이 API) → 화면 하단 "최종 정산 완료하기" → 확정.

## 응답 `200 OK`

```json
{
  "status": "PREVIEW",
  "roomTitle": "제주도 여행",
  "periodStartAt": "2025-01-15T09:00:00+09:00",
  "periodEndAt": "2025-01-20T14:30:00+09:00",
  "budgetAmount": 1000000,
  "totalAmount": 450000,
  "budgetDiffPercent": -55.0,
  "memberCount": 3,
  "perPersonAmount": 150000,
  "receiptCount": 5,
  "entries": [
    {
      "memberId": "...",
      "memberName": "시원",
      "isTreasurer": true,
      "paidAmount": 180000,
      "shareAmount": 150000,
      "balanceAmount": 30000,
      "direction": "RECEIVE"
    },
    {
      "memberId": "...",
      "memberName": "동헌",
      "isTreasurer": false,
      "paidAmount": 120000,
      "shareAmount": 150000,
      "balanceAmount": -30000,
      "direction": "SEND"
    },
    {
      "memberId": "...",
      "memberName": "지수",
      "isTreasurer": false,
      "paidAmount": 150000,
      "shareAmount": 150000,
      "balanceAmount": 0,
      "direction": "NONE"
    }
  ]
}
```

| 필드 | 설명 |
| --- | --- |
| `status` | PREVIEW 또는 SETTLED |
| `periodEndAt` | PREVIEW에서는 조회 시각. 확정 시 그 시점으로 고정 |
| `budgetDiffPercent` | (결제 총액 − 예산) ÷ 예산 × 100. **음수 = 절약**. 예산 0이면 null |
| `perPersonAmount` | 결제 총액 ÷ 활성 멤버 수, 버림 |
| `balanceAmount` | `paidAmount - shareAmount` |
| `direction` | RECEIVE(받을 돈) / SEND(보널 돈) / NONE |

`entries`는 direction 우선(RECEIVE → SEND → NONE), 같은 그룹 안에서는 balanceAmount 절대값 내림차순으로 정렬한다.

## 에러

- `400 NO_ACTIVE_MEMBER`
- `404 ROOM_NOT_FOUND`
- `409 ROOM_ALREADY_SETTLED` — 프론트는 이 코드를 받으면 확정 결과 조회로 전환한다

## 설계 노트 — 나머지 처리

결제 총액 ÷ 멤버 수가 딱 떨어지지 않는 경우가 있다. 100,000 ÷ 3 = 33,333.33이다. 버림으로 계산하면 3명 합계가 99,999원이 되어 1원이 사라진다. 남는 나머지는 **총무의 `shareAmount`에 몰아준다.**

| 멤버 | `shareAmount` |
| --- | --- |
| 총무 | 33,334 |
| 멤버 B | 33,333 |
| 멤버 C | 33,333 |

<aside>
⚠️

**불변식: `sum(balanceAmount) = 0`**

서버는 응답 직전에 이 합을 반드시 검증하고, 0이 아니면 500으로 실패해야 한다. 어긋난 정산 결과를 그대로 보여주면 실제 송금이 맞지 않는다. 행 간 집계라 SQL CHECK로는 표현할 수 없다.

</aside>