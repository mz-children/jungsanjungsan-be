# /api/rooms/{shareCode}/members

도메인: rooms
메서드: GET
설명: 멤버 목록 조회

```
GET /api/rooms/{roomId}/members
```

결제 내역 생성/수정 화면의 결제자 드롭다운, 결제 내역 리스트의 결제자 필터 칩에 쓴다.

## 응답 `200 OK`

```json
{
  "members": [
    { "id": "...", "name": "시원", "isTreasurer": true,  "displayOrder": 0, "receiptCount": 2 },
    { "id": "...", "name": "동헌", "isTreasurer": false, "displayOrder": 1, "receiptCount": 2 }
  ]
}
```

활성 멤버만 `displayOrder`, `createdAt` 순으로 반환한다. `member_idx_room_order` 부분 인덱스를 그대로 탄다.

## 에러

- `404 ROOM_NOT_FOUND`

## 설계 노트

정산방 정보 조회의 `members` 필드와 동일한 스키마다. 방 전체 정보가 필요 없는 화면에서 페이로드를 줄이기 위해 분리했다.