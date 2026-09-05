# /api/rooms/{shareCode}/receipts

도메인: receipts
메서드: GET
설명: 결제 내역 목록 조회 (검색 + 필터 + 무한스크롤)

```jsx
GET /api/rooms/{shareCode}/receipts
```

결제 내역 리스트 화면. 검색 + 결제자 필터 + 무한스크롤.

## 쿼리 파라미터

| 이름 | 타입 | 기본 | 설명 |
| --- | --- | --- | --- |
| `q` | string | — | 결제처 부분 일치 (대소문자 무시) |
| `payerMemberId` | uuid | — | 결제자 필터. 없으면 전체 |
| `cursor` | string | — | 이전 응답의 `nextCursor` |
| `limit` | integer | 20 | 1~50 |

## 응답 `200 OK`

```json
{
  "items": [
    {
      "id": "...",
      "merchant": "올레시장",
      "amount": 150000,
      "paidAt": "2025-01-17T18:20:00+09:00",
      "payer": { "id": "...", "name": "시원" }
    }
  ],
  "nextCursor": "MjAyNS0wMS0xN1QxODoyMDowMCswOTowMHwzZmE4NWY2NA",
  "hasNext": true
}
```

마지막 페이지면 `nextCursor`는 null, `hasNext`는 false다. 정렬은 `paid_at DESC, id DESC`로 `receipt_idx_room_recent` 인덱스를 그대로 탄다.

## 에러

- `400 VALIDATION_ERROR` (잘못된 커서)
- `404 ROOM_NOT_FOUND`

## 설계 노트 — 금액 검색을 제외한 이유

피그마의 검색창 플레이스홀더는 "결제처, 금액 검색"이지만 1차 범위에서는 결제처만 지원한다.

금액 검색은 의미가 모호하다. 150000을 입력했을 때 정확히 일치인지, 콤마를 포함한 표기도 매칭할지, 15만원대를 찾는 범위 검색인지에 따라 구현과 UX가 전부 달라진다. 금액을 문자열로 매칭하면 1500, 21500, 150000을 모두 잡아 결과가 직관에 어긋난다.

기획이 확정되면 `q`가 숫자로만 이뤄진 경우 분기하는 방식으로 추가한다. 응답 스키마는 바뀌지 않으므로 호환성 문제도 없다. 그때까지 피그마의 플레이스홀더는 "결제처 검색"으로 바꾸는 편이 좋다.

결제처 부분 일치는 인덱스 없이 순차 필터로 동작한다. `room_id`로 좁힌 뒤 남는 수백 행 규모에서는 이것이 최적이다 (DB 모델 문서 2.4).