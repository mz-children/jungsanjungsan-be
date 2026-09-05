# /api/rooms/{shareCode}/settlement

도메인: settlement
메서드: POST
설명: 정산 확정 (스냅샷 생성 + 방 read-only 전환)

```jsx
POST /api/rooms/{shareCode}/settlement
```

정산 결과 화면의 "최종 정산 완료하기". 단일 트랜잭션으로 스냅샷을 만들고 방을 SETTLED로 전환한다.

## 요청

```json
{
  "expectedTotalAmount": 450000,
  "expectedReceiptCount": 5
}
```

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `expectedTotalAmount` | integer | N | 미리보기에서 받은 `totalAmount` |
| `expectedReceiptCount` | integer | N | 미리보기에서 받은 `receiptCount` |

## 응답 `201 Created`

미리보기와 동일한 스키마, `status`는 SETTLED.

## 에러

| HTTP | code | 상황 |
| --- | --- | --- |
| 400 | `NO_ACTIVE_MEMBER` | 활성 멤버 0명 |
| 404 | `ROOM_NOT_FOUND` | — |
| 409 | `ROOM_ALREADY_SETTLED` | 이미 확정됨 |
| 409 | `SETTLEMENT_STALE` | 미리보기 이후 결제 내역이 변경됨 |

`SETTLEMENT_STALE`의 details:

```json
{
  "expected": { "totalAmount": 450000, "receiptCount": 5 },
  "actual":   { "totalAmount": 475000, "receiptCount": 6 }
}
```

## 설계 노트 — 낙관적 검증을 두는 이유

미리보기 화면을 띄워둔 상태에서 다른 사람이 결제 내역을 추가할 수 있다. 그대로 확정하면 사용자가 화면에서 확인한 금액과 실제 저장되는 스냅샷이 달라진다. 정산은 되돌릴 수 없으므로 이 불일치는 치명적이다.

`expected` 값을 함께 보내 서버가 재계산 결과와 비교하고, 다르면 409로 막는다. 프론트는 "결제 내역이 변경되었습니다. 다시 확인해 주세요"를 띄우고 미리보기를 새로 불러온다.

선택 필드로 둔 이유는 관리 도구나 재시도 스크립트에서 강제 확정이 필요할 수 있어서다. 정상 흐름에서는 항상 채워 보낸다.

## 설계 노트 — 트랜잭션 순서

방 상태 전환(`UPDATE room SET status = 'SETTLED'`)은 **반드시 마지막**이다. 먼저 하면 `guard_room_settled` 트리거가 이후 단계를 막는다 (DB 모델 문서 5.2).

`settlement` 테이블의 `UNIQUE (room_id)`가 중복 정산을 구조적으로 차단하므로, 동시 요청 두 개 중 하나는 DB 레벨에서 실패한다. 이때도 `409 ROOM_ALREADY_SETTLED`로 변환해 응답한다.