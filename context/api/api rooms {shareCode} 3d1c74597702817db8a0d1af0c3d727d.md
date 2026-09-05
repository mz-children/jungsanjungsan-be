# /api/rooms/{shareCode}

도메인: rooms
메서드: PATCH
설명: 정산방 정보 및 멤버 목록 수정

```
PATCH /api/rooms/{roomId}
```

정산방 수정 화면의 "수정하기". 방 정보와 멤버 목록을 한 트랜잭션에서 함께 처리한다.

## 요청

```json
{
  "title": "제주도 여행 2박 3일",
  "totalBudget": 1200000,
  "thumbnailFileId": null,
  "members": [
    { "id": "a1b2...", "name": "시원" },
    { "id": "c3d4...", "name": "동헌(수정)" },
    { "name": "민수" }
  ]
}
```

`members` 배열은 **선언적 동기화**다. 배열이 곧 수정 후의 최종 상태다.

| 배열 항목 | 동작 |
| --- | --- |
| id 있음 | 해당 멤버 name 갱신 |
| id 없음 | 신규 멤버 INSERT |
| 배열에서 빠짐 | 소프트 삭제 (`deleted_at`) |

`display_order`는 배열 순서로 재부여한다. `members` 키 자체가 없으면 멤버는 건드리지 않는다. null 처리 규칙은 상위 페이지의 공통 규약을 따른다.

## 응답 `200 OK`

정산방 정보 조회와 동일한 스키마.

## 에러

| HTTP | code | 상황 |
| --- | --- | --- |
| 400 | `VALIDATION_ERROR` | 검증 실패, 또는 id가 이 방 소속이 아님 |
| 404 | `ROOM_NOT_FOUND` | — |
| 409 | `ROOM_ALREADY_SETTLED` | status = SETTLED |
| 409 | `DUPLICATE_MEMBER_NAME` | 정규화 후 이름 충돌 |
| 409 | `MEMBER_HAS_RECEIPTS` | 결제 내역이 있는 멤버를 배열에서 제외 |

`MEMBER_HAS_RECEIPTS`의 details:

```json
{
  "members": [
    { "id": "c3d4...", "name": "동헌", "receiptCount": 2 }
  ]
}
```

## 설계 노트 — 개별 멤버 CRUD를 두지 않는 이유

멤버별 엔드포인트로 쪼개면 화면과 어긋난다. 수정 화면은 저장 버튼이 하나뿐이고, 사용자는 이름 변경·추가·삭제를 섞어서 한 번에 제출한다. 개별 API로 나누면 클라이언트가 diff를 계산해 여러 요청을 순서대로 보내야 하고, 중간에 하나가 실패하면 부분 반영 상태가 남는다.

배열 전체를 받아 한 트랜잭션에서 처리하면 전부 성공하거나 전부 실패한다.

대가는 **동시 편집 시 나중 요청이 이긴다**는 점이다. 두 사람이 동시에 수정 화면을 열면 뒤에 저장한 쪽이 앞의 변경을 덮어쓴다. 현재 규모에서는 감수할 만하지만, 문제가 되면 `updatedAt`을 조건부 요청으로 받아 낙관적 잠금을 거는 방식이 있다.