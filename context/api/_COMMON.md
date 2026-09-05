# API 명세

# 엔드포인트 목록

[정산정산API 명세](API%20%EB%AA%85%EC%84%B8/%EC%A0%95%EC%82%B0%EC%A0%95%EC%82%B0API%20%EB%AA%85%EC%84%B8%203d1c7459770280829ab1f3838d8a7f14.csv)

# 개요

| 항목 | 값 |
| --- | --- |
| Base URL | `/api` |
| 포맷 | JSON (`application/json; charset=utf-8`). 파일 업로드만 예외 |
| 인증 | 없음. `shareCode`를 아는 사람이 곧 참여자 |
| 식별자 | URL 식별자는 `room.share_code`. 내부 PK(uuid)는 응답에 노출하지 않음 |
| 통화 | KRW 원 단위 정수. 소수점·문자열 포맷팅 없음 (`450000`) |
| 시각 | ISO 8601 오프셋 표기 (`2025-01-15T09:30:00+09:00`). 저장은 UTC |
| 페이지네이션 | 커서 기반. OFFSET 사용 안 함 |

# 공통 규약

## 권한 모델

로그인 개념이 없다. `shareCode`를 아는 사람은 **조회·생성·수정·삭제를 전부 할 수 있다.** 역할 구분은 존재하지 않으며, 총무(treasurer)는 정산 결과 화면의 안내 문구를 만들기 위한 표시용 플래그일 뿐 권한과 무관하다.

따라서 이 API에는 인증 헤더, 권한 검사, 403 응답이 없다. 접근 제어는 전적으로 "공유 코드를 추측할 수 없다"는 전제에 의존한다.

## 에러 응답

모든 에러는 동일한 형태를 쓴다.

```json
{
  "error": {
    "code": "ROOM_ALREADY_SETTLED",
    "message": "정산이 완료된 방은 수정할 수 없습니다.",
    "details": { "shareCode": "..." }
  }
}
```

`code`는 프론트 분기용 안정적 식별자, `message`는 그대로 노출 가능한 한국어 문구, `details`는 선택이며 코드별로 구조가 다르다.

| HTTP | code | 발생 지점 |
| --- | --- | --- |
| 400 | `VALIDATION_ERROR` | 필수 누락, 길이 초과, 형식 불일치 |
| 400 | `INVALID_PAYER` | `payerMemberId`가 해당 방의 활성 멤버가 아님 |
| 400 | `NO_ACTIVE_MEMBER` | 활성 멤버 0명 상태에서 정산 시도 |
| 404 | `ROOM_NOT_FOUND` | 존재하지 않는 shareCode |
| 404 | `RECEIPT_NOT_FOUND` | 존재하지 않거나 소프트 삭제된 결제 내역 |
| 404 | `SETTLEMENT_NOT_FOUND` | 아직 정산이 확정되지 않은 방의 결과 조회 |
| 409 | `ROOM_ALREADY_SETTLED` | SETTLED 상태 방에 대한 모든 쓰기 시도 |
| 409 | `DUPLICATE_MEMBER_NAME` | 방 내 멤버 이름 중복 (대소문자·앞뒤 공백 무시) |
| 409 | `MEMBER_HAS_RECEIPTS` | 결제 내역이 있는 멤버 삭제 시도 |
| 409 | `SETTLEMENT_STALE` | 미리보기 이후 결제 내역이 변경된 상태에서 확정 시도 |
| 413 | `FILE_TOO_LARGE` | 업로드 용량 초과 |
| 415 | `UNSUPPORTED_MEDIA_TYPE` | 이미지가 아닌 파일 업로드 |

`VALIDATION_ERROR`의 details는 필드 단위 배열이다.

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "입력값을 확인해 주세요.",
    "details": {
      "fields": [
        { "field": "title", "reason": "정산방 이름은 50자 이하여야 합니다." },
        { "field": "members[2].name", "reason": "멤버 이름을 입력해 주세요." }
      ]
    }
  }
}
```

## 정산 완료 상태의 쓰기 차단

`room.status`가 SETTLED가 되면 멤버와 결제 내역이 읽기 전용이 된다. 다음 엔드포인트는 전부 `409 ROOM_ALREADY_SETTLED`를 반환한다.

- 정산방 수정
- 결제 내역 생성 / 수정 / 삭제
- 정산 미리보기 / 정산 확정

DB 트리거 `guard_room_settled`가 최종 방어선이지만, 애플리케이션 레이어에서 먼저 검사해 정확한 에러 코드를 내려준다. 트리거의 check_violation이 그대로 올라오면 어떤 규칙에 걸렸는지 프론트가 구분할 수 없다.

## 커서 페이지네이션

커서는 불투명(opaque) 문자열이다. 클라이언트는 내용을 해석하지 않고 `nextCursor`를 그대로 다음 요청에 실어 보낸다.

```
cursor = base64url("{paidAt ISO8601}|{receiptId}")
```

`(paid_at, id)` 튜플 비교로 동작하므로 무한스크롤 도중 새 결제가 추가돼도 항목이 밀리거나 중복되지 않는다. `receipt_idx_room_recent` 인덱스를 그대로 탄다.

## PATCH의 null 처리

PATCH는 **키가 존재하는 필드만** 수정한다. 선택 필드를 비우려면 명시적으로 null을 보낸다.

| 요청 본문 | 동작 |
| --- | --- |
| `{}` | 변경 없음 |
| `{ "description": "메모" }` | 설명을 "메모"로 변경 |
| `{ "description": null }` | 설명 삭제 |

# 화면별 호출 매핑

| 화면 | 호출 |
| --- | --- |
| `/` | 없음 (공유 링크 복사는 클라이언트 처리) |
| `/room/create` | `POST /files` (썸네일 선택 시) |
| `/room/confirm` | 없음 (클라이언트 상태만 표시) |
| `/room/done` | `POST /rooms` — 진입 직전 1회 |
| `/room/:shareCode` | `GET /rooms/:shareCode/summary` |
| `/room/:shareCode` 드로어 | `GET /rooms/:shareCode` (썸네일·제목) |
| `/room/:shareCode/edit` | `GET /rooms/:shareCode` → `POST /files` → `PATCH /rooms/:shareCode` |
| `/room/:shareCode/receipt` | `GET /rooms/:shareCode/members`  • `GET /rooms/:shareCode/receipts` |
| `/room/:shareCode/receipt/create` | `GET /members` → `POST /files` → `POST /receipts` |
| `/room/:shareCode/receipt/:rid` | `GET /receipts/:rid` |
| `/room/:shareCode/receipt/:rid/edit` | `GET /receipts/:rid`  • `GET /members` → `PATCH /receipts/:rid` |
| `/room/:shareCode/receipt/:rid` 삭제 | `DELETE /receipts/:rid` |
| `/room/:shareCode/result` (확정 전) | `GET /settlement/preview` → `POST /settlement` |
| `/room/:shareCode/result` (확정 후) | `GET /settlement` |

정산 결과 화면 진입 시에는 `GET /settlement`를 먼저 호출하고, `404 SETTLEMENT_NOT_FOUND`가 오면 `GET /settlement/preview`로 넘어가는 방식이 안전하다. 반대 순서로 하면 이미 확정된 방에서 불필요한 409가 먼저 발생한다.

# DB 모델과의 차이

## `room.share_code`를 URL 식별자로 사용

DB 모델 문서의 설계를 그대로 따른다. `share_code`가 URL 노출용 공개 식별자고, 라우팅은 `/room/{shareCode}`이며 API 경로 파라미터도 `{shareCode}`다.

내부 PK인 `room.id`(uuid)는 **응답에 전혀 노출하지 않는다.** 둘 다 내려주면 식별자가 두 개가 되어 프론트가 어느 쪽을 써야 하는지 모호해지고, 내부 PK를 숨기려는 설계 의도도 무색해진다.

`share_code` 생성 규칙은 다음과 같다.

| 항목 | 값 |
| --- | --- |
| 생성 주체 | 애플리케이션. INSERT 직전에 생성해 같이 넣는다 |
| 형식 | `^[A-Za-z0-9_-]{8,32}$` — `room_share_code_fmt` 제약 |
| 권장 길이 | 12자 nanoid. 약 71비트 엔트로피 |
| 충돌 처리 | UNIQUE 위반 시 재생성 후 재시도, 최대 3회 |

<aside>
⚠️

**uuid 대신 공유 코드를 쓰는 이유.** 추측 불가능성만 놓고 보면 uuid v4가 122비트로 더 강하다. 그러나 이 서비스는 링크를 메신저로 주고받는 것이 사실상 유일한 참여 경로라 링크 길이가 그대로 UX다. 12자 nanoid는 약 71비트로 무차별 대입 방어에 충분하면서 링크가 짧다. 대가는 생성·충돌 처리 코드가 필요하고 식별자가 사실상 둘(PK + 공유 코드)이 된다는 점인데, 후자는 API 경계에서 `share_code`만 노출해 해결한다.~32자 영숫자 코드보다 강하고, `share_code` 생성·충돌 처리 코드가 통째로 사라진다. 다만 `/room/3fa85f64-5717-4562-b3fc-2c963f66afa6`는 카카오톡 공유 시 눈에 거슬린다. 짧은 링크가 UX상 중요하다면 `share_code`를 살리고 경로 파라미터를 `shareCode`로 바꾸는 편이 낫다. **API 구현 전에 확정해야 한다.**

</aside>

## `settlement_entry.member_id`의 NULL 허용

DB에서는 `ON DELETE SET NULL`이라 멤버가 하드 삭제되면 `member_id`가 NULL이 된다. API 응답의 `entries[].memberId`도 null일 수 있다.

다만 `receipt_payer_fk`의 `ON DELETE RESTRICT` 때문에 결제 내역이 있는 멤버는 하드 삭제 자체가 막힌다. 실제로 발생하기 어려운 경로지만, 프론트는 `memberId`를 key로 쓰지 말고 배열 인덱스나 `memberName`을 함께 쓰는 편이 안전하다.

## 감사 로그 없음

누가 언제 어떤 결제 내역을 수정했는지 추적할 수 없다. 인증이 없으므로 "누가"를 기록할 수단 자체가 없다.

# 알려진 한계

## 링크를 아는 사람이 모든 권한을 가짐

공유 코드가 유출되면 제3자가 결제 내역을 추가·수정·삭제하고 정산까지 확정할 수 있다. 정산 확정은 되돌릴 수 없으므로 피해가 크다.

12자 nanoid는 무차별 대입이 현실적으로 불가능하지만, 링크 자체가 새면 방어 수단이 없다. 필요해지면 다음 중 하나를 검토한다.

- 조회 전용 코드와 편집 코드 분리
- 정산 확정에만 별도 확인 절차 추가 (방 생성 시 발급한 코드 입력 등)

## 정산 확정 취소 불가

`SETTLED → ACTIVE` 역방향 전이가 정의되지 않았다. 실수로 확정하면 방을 새로 만드는 수밖에 없다.

되돌리기를 지원하려면 settlement 행 삭제 + `room.status` 복구를 한 트랜잭션으로 처리하는 `DELETE /rooms/:shareCode/settlement`를 추가한다. 스냅샷을 지우는 동작이라 "확정 후 N분 이내"처럼 제한을 거는 편이 낫다.

## 대시보드 집계의 실시간성

대시보드 조회는 매번 `sum(amount)`을 계산한다. 결제 건수가 수천 건을 넘으면 room에 캐시 컬럼을 두고 트리거로 갱신하는 방식을 검토할 수 있다. 정합성 관리 비용이 생기므로 실제 성능 문제가 확인된 후에 도입한다.

## 증빙 이미지 1장 제한

`receipt.image_file_id`가 단일 FK다. 여러 장을 첨부하려면 `receipt_image` 조인 테이블 분리가 필요하고, API의 `imageFileId`도 `imageFileIds` 배열로 바뀐다. 응답 스키마가 깨지는 변경이다.

## 명세에 포함되지 않은 것

| 항목 | 사유 |
| --- | --- |
| 정산방 삭제 | 화면에 진입점이 없음 |
| 금액 검색 | 기획 미확정. 결제 내역 목록 조회 페이지 참고 |
| 일자별 바 차트, 도넛 차트 | 기획서상 레거시로 분류 |
| Rate limiting | 인증이 없어 IP 기준밖에 없음. 운영 단계에서 검토 |