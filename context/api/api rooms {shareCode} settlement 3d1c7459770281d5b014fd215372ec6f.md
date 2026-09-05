# /api/rooms/{shareCode}/settlement

도메인: settlement
메서드: GET
설명: 확정된 정산 결과 조회 (스냅샷)

```
GET /api/rooms/{roomId}/settlement
```

확정 후 정산 결과 화면에 재방문했을 때.

## 응답 `200 OK`

미리보기와 동일한 스키마, `status`는 SETTLED.

값은 전부 `settlement` / `settlement_entry`에 굳어 있는 스냅샷이다. 이후 방 이름이나 멤버 이름이 바뀜어도 이 응답은 변하지 않는다.

## 에러

- `404 ROOM_NOT_FOUND`
- `404 SETTLEMENT_NOT_FOUND` — 방은 있지만 아직 ACTIVE인 경우

## 설계 노트

프론트는 `SETTLEMENT_NOT_FOUND`를 받으면 미리보기로 전환한다.

정산 결과 화면 진입 시에는 이 API를 먼저 호출하고, 404가 오면 미리보기로 넘어가는 순서가 안전하다. 반대 순서로 하면 이미 확정된 방에서 불필요한 409가 먼저 발생한다.