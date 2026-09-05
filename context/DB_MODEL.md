# 정산정산 — 데이터베이스 명세서

| 항목      | 값                                                        |
| --------- | --------------------------------------------------------- |
| DBMS      | PostgreSQL 15+                                            |
| 문자셋    | UTF-8                                                     |
| 통화 단위 | KRW 원 단위 정수 (`bigint`). 소수점 없음                  |
| 시각 타입 | 전부 `timestamptz` (UTC 저장, 앱에서 `Asia/Seoul` 렌더링) |
| 식별자    | `uuid` (`gen_random_uuid()`)                              |
| 인증 모델 | 없음. `room.share_code` 링크를 아는 사람이 곧 참여자      |
| 확장      | `pgcrypto`                                                |

---

## 1. 개요

### 1.1 도메인 모델

여행 경비 정산 서비스. **정산방**(room) 하나가 여행 하나에 대응하고, 그 안에 **멤버**(member)와 **결제 내역**(receipt)이 속한다. 여행이 끝나면 정산을 완료하고, 그 시점의 계산 결과를 **정산 스냅샷**(settlement)으로 굳혀서 보관한다.

```
file_object ──┬──< room ──┬──< member ──┐
              │           │             │
              └──< receipt >────────────┘
                          │
                          └──< settlement ──< settlement_entry
```

### 1.2 테이블 목록

| #   | 테이블             | 역할                     | 삭제 정책              |
| --- | ------------------ | ------------------------ | ---------------------- |
| 1   | `file_object`      | 업로드 이미지 메타데이터 | 하드 삭제 (배치 정리)  |
| 2   | `room`             | 정산방                   | 하드 삭제 (CASCADE)    |
| 3   | `member`           | 여행 멤버                | 소프트 삭제            |
| 4   | `receipt`          | 결제 내역                | 소프트 삭제            |
| 5   | `settlement`       | 정산 결과 스냅샷         | 방 삭제 시 CASCADE     |
| 6   | `settlement_entry` | 멤버별 정산 내역         | 스냅샷 삭제 시 CASCADE |

### 1.3 ENUM 타입

| 타입                   | 값                        | 설명                    |
| ---------------------- | ------------------------- | ----------------------- |
| `room_status`          | `ACTIVE`, `SETTLED`       | 정산방 상태             |
| `settlement_direction` | `RECEIVE`, `SEND`, `NONE` | 송금 방향 (뷰에서 파생) |

---

## 2. 테이블 명세

### 2.1 `file_object` — 업로드 이미지

정산방 썸네일과 결제 증빙 이미지가 동일한 업로드 파이프라인을 타므로 단일 테이블로 통합했다. 실제 바이너리는 오브젝트 스토리지(S3 등)에 두고 여기엔 메타데이터만 저장한다.

| 컬럼            | 타입          | NULL | 기본값              | 설명                  |
| --------------- | ------------- | ---- | ------------------- | --------------------- |
| `id`            | `uuid`        | N    | `gen_random_uuid()` | PK                    |
| `storage_key`   | `text`        | N    |                     | 스토리지 경로. UNIQUE |
| `original_name` | `text`        | N    |                     | 업로드 시 원본 파일명 |
| `content_type`  | `text`        | N    |                     | MIME 타입             |
| `byte_size`     | `bigint`      | N    |                     | 파일 크기             |
| `created_at`    | `timestamptz` | N    | `now()`             |                       |

**제약**

| 이름                     | 내용                          |
| ------------------------ | ----------------------------- |
| `file_object_size_pos`   | `byte_size > 0`               |
| `file_object_image_only` | `content_type LIKE 'image/%'` |

**설계 노트 — 이미지 치수를 저장하지 않는 이유**

이미지 가로/세로 픽셀은 보통 레이아웃 시프트(CLS) 방지를 위해 저장한다. 로딩 전에 공간을 미리 확보하려는 것이다. 그러나 이 서비스의 이미지 노출 지점은 두 곳뿐이고 **둘 다 고정 크기 박스**다.

| 위치                   | 크기      |
| ---------------------- | --------- |
| 정산방 썸네일 (드로어) | 272 × 132 |
| 증빙 이미지 업로더     | 354 × 100 |

`object-fit: cover`로 채우면 원본 비율과 무관하게 레이아웃이 고정되므로 실측값이 필요 없다. 반대로 저장하면 업로드 시점에 이미지를 디코딩해야 하고(`sharp` 등), 이후 리사이즈·크롭 기능이 추가되면 갱신 누락으로 값이 실제와 어긋날 수 있다. 쓰이지 않는 컬럼이 부정확해지는 것이 가장 나쁜 상태다.

`byte_size`는 업로드 용량 제한 검증과 스토리지 사용량 집계에 실제로 쓰이므로 유지한다.

갤러리형 배치(masonry)처럼 원본 비율이 필요한 UI가 생기면 그때 `ALTER TABLE ... ADD COLUMN`으로 추가한다. NULL 허용 컬럼이라 무중단으로 붙일 수 있다.

---

### 2.2 `room` — 정산방

| 컬럼                | 타입          | NULL | 기본값              | 설명                                     |
| ------------------- | ------------- | ---- | ------------------- | ---------------------------------------- |
| `id`                | `uuid`        | N    | `gen_random_uuid()` | PK                                       |
| `share_code`        | `text`        | N    |                     | URL 노출용 공개 식별자. UNIQUE           |
| `title`             | `text`        | N    |                     | 정산방 이름                              |
| `total_budget`      | `bigint`      | N    |                     | 총예산 (원)                              |
| `thumbnail_file_id` | `uuid`        | Y    |                     | → `file_object.id`, `ON DELETE SET NULL` |
| `status`            | `room_status` | N    | `'ACTIVE'`          |                                          |
| `settled_at`        | `timestamptz` | Y    |                     | 정산 완료 시각                           |
| `created_at`        | `timestamptz` | N    | `now()`             | 정산 기간의 시작점                       |
| `updated_at`        | `timestamptz` | N    | `now()`             | 트리거로 자동 갱신                       |

**제약**

| 이름                       | 내용                                                          |
| -------------------------- | ------------------------------------------------------------- |
| `room_title_not_blank`     | `btrim(title) <> ''`                                          |
| `room_title_len`           | 50자 이하                                                     |
| `room_budget_nonneg`       | `total_budget >= 0`                                           |
| `room_share_code_fmt`      | `^[A-Za-z0-9_-]{8,32}$`                                       |
| `room_settled_consistency` | `SETTLED`면 `settled_at` 필수, `ACTIVE`면 `settled_at`은 NULL |

**설계 노트**

- `share_code`를 PK와 분리한 이유: 계정 없이 링크만으로 접근하는 구조라 URL에 내부 PK를 노출하지 않는 편이 안전하고, 짧은 코드가 공유 UX에도 유리하다. 라우팅은 `/room/{share_code}`.
- **1인당 예산은 저장하지 않는다.** `total_budget ÷ 활성 멤버 수`로 계산되는 파생값이며, 멤버가 추가·삭제될 때마다 값이 바뀌므로 저장하면 정합성 관리 비용만 늘어난다. `room_dashboard_view`에서 계산한다.
- 결제 총액, 진행률(%)도 같은 이유로 저장하지 않는다.

---

### 2.3 `member` — 여행 멤버

계정이 아니라 이름표에 가깝다. 로그인 개념이 없으므로 인증 관련 컬럼은 두지 않는다.

| 컬럼            | 타입          | NULL | 기본값              | 설명                             |
| --------------- | ------------- | ---- | ------------------- | -------------------------------- |
| `id`            | `uuid`        | N    | `gen_random_uuid()` | PK                               |
| `room_id`       | `uuid`        | N    |                     | → `room.id`, `ON DELETE CASCADE` |
| `name`          | `text`        | N    |                     | 멤버 이름                        |
| `is_treasurer`  | `boolean`     | N    | `false`             | 총무 여부                        |
| `display_order` | `integer`     | N    | `0`                 | 표시 순서                        |
| `created_at`    | `timestamptz` | N    | `now()`             |                                  |
| `updated_at`    | `timestamptz` | N    | `now()`             | 트리거로 자동 갱신               |
| `deleted_at`    | `timestamptz` | Y    |                     | 소프트 삭제 시각                 |

**제약**

| 이름                    | 내용                                            |
| ----------------------- | ----------------------------------------------- |
| `member_name_not_blank` | `btrim(name) <> ''`                             |
| `member_name_len`       | 20자 이하                                       |
| `member_room_id_uq`     | `UNIQUE (room_id, id)` — `receipt` 복합 FK 대상 |

**인덱스**

| 이름                        | 정의                                                            | 목적                                      |
| --------------------------- | --------------------------------------------------------------- | ----------------------------------------- |
| `member_uq_room_name_alive` | `UNIQUE (room_id, lower(btrim(name))) WHERE deleted_at IS NULL` | 방 내 이름 중복 금지 (대소문자·공백 무시) |
| `member_uq_room_treasurer`  | `UNIQUE (room_id) WHERE is_treasurer AND deleted_at IS NULL`    | 방당 총무 1명                             |
| `member_idx_room_order`     | `(room_id, display_order, created_at) WHERE deleted_at IS NULL` | 멤버 목록 조회                            |

**설계 노트**

- **소프트 삭제를 쓰는 이유**: `receipt.payer_member_id`가 멤버를 참조한다. 하드 삭제하면 결제자가 사라진 영수증이 생겨 정산 계산이 깨진다.
- `UNIQUE (room_id, id)`는 언뜻 중복처럼 보이지만 `receipt`의 복합 FK 대상으로 반드시 필요하다. 2.4 참고.

---

### 2.4 `receipt` — 결제 내역

| 컬럼              | 타입          | NULL | 기본값              | 설명                                                 |
| ----------------- | ------------- | ---- | ------------------- | ---------------------------------------------------- |
| `id`              | `uuid`        | N    | `gen_random_uuid()` | PK                                                   |
| `room_id`         | `uuid`        | N    |                     | → `room.id`, `ON DELETE CASCADE`                     |
| `payer_member_id` | `uuid`        | N    |                     | 결제자                                               |
| `merchant`        | `text`        | N    |                     | 결제처                                               |
| `amount`          | `bigint`      | N    |                     | 금액 (원)                                            |
| `paid_at`         | `timestamptz` | N    |                     | 결제일시                                             |
| `description`     | `text`        | Y    |                     | 설명                                                 |
| `image_file_id`   | `uuid`        | Y    |                     | 증빙 이미지 → `file_object.id`, `ON DELETE SET NULL` |
| `created_at`      | `timestamptz` | N    | `now()`             |                                                      |
| `updated_at`      | `timestamptz` | N    | `now()`             | 트리거로 자동 갱신                                   |
| `deleted_at`      | `timestamptz` | Y    |                     | 소프트 삭제 시각                                     |

**제약**

| 이름                         | 내용                                                                     |
| ---------------------------- | ------------------------------------------------------------------------ |
| `receipt_room_fk`            | `FK (room_id) → room(id) ON DELETE CASCADE`                              |
| `receipt_payer_fk`           | `FK (room_id, payer_member_id) → member(room_id, id) ON DELETE RESTRICT` |
| `receipt_amount_pos`         | `amount > 0`                                                             |
| `receipt_merchant_not_blank` | `btrim(merchant) <> ''`                                                  |
| `receipt_merchant_len`       | 100자 이하                                                               |
| `receipt_desc_len`           | 500자 이하                                                               |

**인덱스**

| 이름                            | 정의                                                                         | 목적                                        |
| ------------------------------- | ---------------------------------------------------------------------------- | ------------------------------------------- |
| `receipt_idx_room_recent`       | `(room_id, paid_at DESC, id DESC) WHERE deleted_at IS NULL`                  | 최신순 커서 페이지네이션, 대시보드 최근 3건 |
| `receipt_idx_room_payer_recent` | `(room_id, payer_member_id, paid_at DESC, id DESC) WHERE deleted_at IS NULL` | 결제자 필터 + 최신순                        |

**설계 노트 — 검색용 인덱스를 두지 않는 이유**

결제 내역 리스트는 결제처와 금액으로 검색하지만, 이를 위한 인덱스는 만들지 않는다.

모든 조회는 `WHERE room_id = ?`로 시작한다. 이 조건을 통과하고 남는 행은 여행 하나당 수백 건 수준이며, 그 정도 규모에서는 문자열 비교를 순차로 처리하는 편이 인덱스를 경유하는 것보다 빠르다. 플래너도 같은 판단을 내려 인덱스를 무시한다. 즉 **쓰기 비용만 지불하고 읽기 이득은 없는 상태**가 된다.

특히 부분일치 검색용 GIN + `pg_trgm` 조합은 문자열 하나를 3글자 조각 수십 개로 쪼개 색인하므로, 이 스키마에서 쓰기 비용이 가장 비싼 인덱스가 된다. 확장 설치가 배포 환경에 따라 제약이 되는 점도 부담이다.

`merchant ILIKE '%...%'`와 `amount::text LIKE '%...%'` 쿼리(5.1)는 **인덱스 없이 그대로 동작한다.** 성능 문제가 실제로 관측되면 그때 `CREATE INDEX CONCURRENTLY`로 무중단 추가하면 된다.

**재검토 기준**

| 조건                                    | 대응                                 |
| --------------------------------------- | ------------------------------------ |
| 방 하나당 결제 내역 5,000건 초과        | `(room_id, amount)` B-tree 추가 검토 |
| 여러 정산방을 가로지르는 검색 기능 추가 | `pg_trgm` + GIN 재검토               |

후자가 더 현실적인 트리거다. 방 경계를 넘는 순간 `room_id`로 먼저 좁힌다는 전제가 깨지기 때문이다.

**설계 노트 — 복합 FK**

`receipt_payer_fk`가 이 스키마의 핵심 안전장치다. 단순히 `payer_member_id → member(id)`로 걸면 **다른 방의 멤버를 결제자로 지정하는 것을 막지 못한다.** `(room_id, payer_member_id)` 쌍으로 참조하면 결제자가 반드시 그 정산방 소속임을 DB가 보장한다. 이를 위해 `member`에 `UNIQUE (room_id, id)`가 필요하다.

`ON DELETE RESTRICT`는 방어선이 하나 더 있다는 뜻이다 — 멤버 하드 삭제 자체가 차단된다.

---

### 2.5 `settlement` — 정산 결과 스냅샷

정산 완료 시점의 계산 결과를 굳혀서 보관한다. 나중에 방 이름이나 멤버 이름이 바뀌어도 "그때 누가 얼마를 보냈어야 했는지"는 변하지 않아야 하므로, 참조 대신 값을 복사해 둔다.

| 컬럼                | 타입          | NULL | 기본값              | 설명                                         |
| ------------------- | ------------- | ---- | ------------------- | -------------------------------------------- |
| `id`                | `uuid`        | N    | `gen_random_uuid()` | PK                                           |
| `room_id`           | `uuid`        | N    |                     | → `room.id`, **UNIQUE**, `ON DELETE CASCADE` |
| `room_title`        | `text`        | N    |                     | 스냅샷                                       |
| `budget_amount`     | `bigint`      | N    |                     | 스냅샷                                       |
| `period_start_at`   | `timestamptz` | N    |                     | = `room.created_at`                          |
| `period_end_at`     | `timestamptz` | N    |                     | 정산 완료 시점                               |
| `total_amount`      | `bigint`      | N    |                     | 결제 총액                                    |
| `member_count`      | `integer`     | N    |                     | 정산 대상 멤버 수                            |
| `per_person_amount` | `bigint`      | N    |                     | 1인당 실비용                                 |
| `receipt_count`     | `integer`     | N    |                     | 결제 건수                                    |
| `created_at`        | `timestamptz` | N    | `now()`             |                                              |

**제약**

| 이름                          | 내용                               |
| ----------------------------- | ---------------------------------- |
| `settlement_member_count_pos` | `member_count > 0`                 |
| `settlement_total_nonneg`     | `total_amount >= 0`                |
| `settlement_receipts_nonneg`  | `receipt_count >= 0`               |
| `settlement_period_order`     | `period_end_at >= period_start_at` |

`UNIQUE (room_id)`로 **중복 정산을 구조적으로 차단**한다. 애플리케이션이 정산 완료 API를 두 번 호출해도 두 번째는 DB에서 실패한다.

---

### 2.6 `settlement_entry` — 멤버별 정산 내역

| 컬럼             | 타입      | NULL | 기본값              | 설명                                   |
| ---------------- | --------- | ---- | ------------------- | -------------------------------------- |
| `id`             | `uuid`    | N    | `gen_random_uuid()` | PK                                     |
| `settlement_id`  | `uuid`    | N    |                     | → `settlement.id`, `ON DELETE CASCADE` |
| `member_id`      | `uuid`    | Y    |                     | → `member.id`, `ON DELETE SET NULL`    |
| `member_name`    | `text`    | N    |                     | 스냅샷                                 |
| `is_treasurer`   | `boolean` | N    | `false`             | 스냅샷                                 |
| `paid_amount`    | `bigint`  | N    |                     | 이 멤버가 실제로 낸 금액               |
| `share_amount`   | `bigint`  | N    |                     | 이 멤버가 부담해야 할 몫               |
| `balance_amount` | `bigint`  | N    | `GENERATED`         | `paid_amount - share_amount` (STORED)  |

**제약**

| 이름                         | 내용                                |
| ---------------------------- | ----------------------------------- |
| `settlement_entry_uq`        | `UNIQUE (settlement_id, member_id)` |
| `settlement_entry_paid_pos`  | `paid_amount >= 0`                  |
| `settlement_entry_share_pos` | `share_amount >= 0`                 |

**`balance_amount` 해석**

| 값   | 의미        | UI 표기                        |
| ---- | ----------- | ------------------------------ |
| 양수 | 더 냈음     | `+₩30,000 총무에게 받으세요`   |
| 음수 | 덜 냈음     | `-₩30,000 총무에게 보내주세요` |
| 0    | 정산 불필요 | —                              |

---

## 3. 트리거

### 3.1 `set_updated_at()`

`room`, `member`, `receipt`의 `BEFORE UPDATE`에 연결. `updated_at`을 `now()`로 갱신한다.

### 3.2 `guard_room_settled()`

정산이 완료된 방을 읽기 전용으로 만든다. `receipt`와 `member`의 `BEFORE INSERT OR UPDATE OR DELETE`에 연결되며, 대상 방의 `status`가 `SETTLED`면 예외를 던진다.

```
ERRCODE: check_violation
메시지 : 정산이 완료된 방은 수정할 수 없습니다 (room_id=...)
```

정산 스냅샷은 계산 시점의 결제 내역을 전제로 만들어졌으므로, 사후 변경을 허용하면 스냅샷과 원장이 어긋난다.

### 3.3 `guard_member_has_receipts()`

`member`의 `BEFORE UPDATE`에 연결. `deleted_at`이 `NULL → NOT NULL`로 바뀌는 순간(= 소프트 삭제)에, 그 멤버 앞으로 살아 있는 결제 내역이 있으면 예외를 던진다.

```
ERRCODE: check_violation
메시지 : 결제 내역이 있는 멤버는 삭제할 수 없습니다 (member=...)
```

정산방 수정 화면에서 멤버를 지우려 할 때 이 규칙에 걸린다. **프론트엔드에서 미리 안내해야 할 케이스다** — 삭제 버튼을 비활성화하거나, "결제 내역 3건이 있어 삭제할 수 없습니다" 같은 메시지를 보여주는 편이 낫다.

---

## 4. 뷰

### 4.1 `room_dashboard_view`

`/room/{id}` 대시보드 한 번에 조회.

| 컬럼                                       | 설명                                          |
| ------------------------------------------ | --------------------------------------------- |
| `room_id`, `share_code`, `title`, `status` | 기본 정보                                     |
| `total_budget`, `thumbnail_file_id`        |                                               |
| `created_at`, `settled_at`                 |                                               |
| `member_count`                             | 활성 멤버 수                                  |
| `budget_per_person`                        | `total_budget ÷ member_count` (버림)          |
| `total_paid`                               | 결제 총액                                     |
| `receipt_count`                            | 결제 건수                                     |
| `usage_percent`                            | `total_paid ÷ total_budget × 100`, 소수 1자리 |

프로그레스바 5단계 색상은 `usage_percent`로 프론트에서 분기한다.

| 구간     | 상태 |
| -------- | ---- |
| `< 25`   | 여유 |
| `< 50`   | 정상 |
| `< 75`   | 주의 |
| `< 100`  | 경고 |
| `>= 100` | 초과 |

`LEFT JOIN LATERAL`로 멤버 집계와 결제 집계를 각각 서브쿼리로 분리했다. 하나의 `JOIN`으로 묶으면 카티전 곱이 생겨 합계가 부풀려진다.

### 4.2 `settlement_guide_view`

`/room/{id}/result` 정산 결과 화면용. `settlement`과 `settlement_entry`를 조인하고 다음 두 컬럼을 추가로 계산한다.

| 컬럼                  | 설명                                                                                 |
| --------------------- | ------------------------------------------------------------------------------------ |
| `budget_diff_percent` | `(total_amount - budget_amount) ÷ budget_amount × 100`. **음수 = 절약, 양수 = 초과** |
| `direction`           | `balance_amount` 부호로 파생 (`RECEIVE` / `SEND` / `NONE`)                           |

---

## 5. 주요 쿼리

### 5.1 결제 내역 리스트 (검색 + 필터 + 무한스크롤)

```sql
SELECT r.id, r.merchant, r.amount, r.paid_at, m.name AS payer_name
FROM receipt r
JOIN member m ON m.id = r.payer_member_id
WHERE r.room_id = $1
  AND r.deleted_at IS NULL
  AND ($2::uuid IS NULL OR r.payer_member_id = $2)              -- 결제자 필터
  AND ($3::text IS NULL OR r.merchant ILIKE '%' || $3 || '%'
                        OR r.amount::text LIKE '%' || $3 || '%')
  AND ($4::timestamptz IS NULL OR (r.paid_at, r.id) < ($4, $5)) -- 커서
ORDER BY r.paid_at DESC, r.id DESC
LIMIT 20;
```

`OFFSET` 대신 `(paid_at, id)` 튜플 커서를 쓴다. 무한스크롤 도중 새 결제가 추가돼도 항목이 밀리거나 중복되지 않는다.

### 5.2 정산 완료 처리

단일 트랜잭션으로 처리하며, 순서가 중요하다.

```sql
BEGIN;
  -- 1. 방을 잠그고 상태 확인 (동시 정산 방지)
  SELECT id FROM room WHERE id = $1 AND status = 'ACTIVE' FOR UPDATE;

  -- 2. 스냅샷 생성
  WITH stat AS (
      SELECT COALESCE(sum(amount),0) AS total, count(*)::int AS cnt
      FROM receipt WHERE room_id = $1 AND deleted_at IS NULL
  ), mem AS (
      SELECT count(*)::int AS n FROM member
      WHERE room_id = $1 AND deleted_at IS NULL
  )
  INSERT INTO settlement (room_id, room_title, budget_amount,
                          period_start_at, period_end_at,
                          total_amount, member_count,
                          per_person_amount, receipt_count)
  SELECT r.id, r.title, r.total_budget, r.created_at, now(),
         stat.total, mem.n, stat.total / mem.n, stat.cnt
  FROM room r, stat, mem WHERE r.id = $1;

  -- 3. settlement_entry 삽입 (앱에서 계산, 6.2 참고)

  -- 4. 방 상태 전환 — 반드시 마지막.
  --    guard_room_settled 트리거 때문에 먼저 하면 2~3단계가 막힌다.
  UPDATE room SET status = 'SETTLED', settled_at = now() WHERE id = $1;
COMMIT;
```

### 5.3 고아 파일 정리 (배치)

업로드했지만 폼을 제출하지 않은 이미지가 쌓인다. 24시간 이상 지난 미참조 파일을 정리한다.

```sql
DELETE FROM file_object f
WHERE f.created_at < now() - interval '24 hours'
  AND NOT EXISTS (SELECT 1 FROM room    WHERE thumbnail_file_id = f.id)
  AND NOT EXISTS (SELECT 1 FROM receipt WHERE image_file_id     = f.id);
```

DB 행 삭제와 스토리지 객체 삭제를 함께 처리해야 한다.

---

## 6. 비즈니스 규칙

### 6.1 총무 (Treasurer)

정산 결과 화면은 "총무에게 받으세요 / 보내주세요"라는 **허브 앤 스포크** 정산 방식을 쓴다. 멤버끼리 N:N으로 송금하지 않고 전부 총무를 거친다.

`member.is_treasurer`로 지정하며 방당 최대 1명이다. 미지정 시 `display_order`가 가장 낮은 멤버(= 생성 시 첫 번째로 입력된 멤버)를 총무로 간주한다.

> **미결 사항.** 기획서와 피그마의 정산방 생성 화면에는 총무 지정 UI가 없다. 첫 멤버를 자동 지정할지, 생성 폼에 선택 UI를 추가할지 확정이 필요하다.

### 6.2 정산 계산

```
1인당 실비용 = 결제 총액 ÷ 활성 멤버 수
balance      = 그 멤버가 낸 금액 − 그 멤버가 부담할 몫
```

**나머지 처리.** 나눗셈이 딱 떨어지지 않는 경우가 있다. 450,000 ÷ 3 = 150,000이지만 100,000 ÷ 3 = 33,333.33이다.

`share_amount`를 멤버별로 명시 저장하는 이유가 여기 있다. 나머지를 총무에게 몰아준다.

| 멤버   | `share_amount` |
| ------ | -------------- |
| 총무   | 33,334         |
| 멤버 B | 33,333         |
| 멤버 C | 33,333         |

**불변식: `sum(balance_amount) = 0`**

이 조건은 SQL `CHECK`로 표현할 수 없다(행 간 집계라서). `settlement_entry` 삽입 직후 애플리케이션에서 반드시 검증하고, 어긋나면 트랜잭션을 롤백해야 한다.

정산방 생성 화면의 "1인당 예산 ₩333,333"도 버림 표기이므로 이 규칙과 일관된다.

### 6.3 상태 전이

```
ACTIVE ──[정산 완료]──> SETTLED
```

역방향 전이는 정의하지 않는다. `SETTLED` 상태에서는 멤버와 결제 내역이 모두 읽기 전용이 된다(3.2 참고).

---

## 7. 알려진 한계와 확장 지점

### 7.1 검색이 순차 필터에 의존함

결제처와 금액 검색에는 인덱스가 없다(2.4 참고). `room_id`로 좁힌 뒤 남는 수백 행을 순차 비교하는 방식이며, 현재 규모에서는 이것이 최적이다.

규모가 커지면 두 방향으로 대응한다. 결제처는 `pg_trgm` + GIN을 추가하고, 금액은 검색어가 숫자일 때만 범위 조건으로 분기해 B-tree를 타게 한다.

```sql
AND ($3 ~ '^[0-9,]+$'
     AND r.amount BETWEEN $3_num * 0.9 AND $3_num * 1.1)
```

두 경우 모두 `CREATE INDEX CONCURRENTLY`로 무중단 추가가 가능하므로, 실제 지연이 관측된 뒤에 도입하면 된다.

### 7.2 대시보드 집계의 실시간성

`room_dashboard_view`는 매 조회마다 `sum(amount)`을 계산한다. 결제 건수가 수천 건을 넘으면 `room`에 `cached_total_paid` 컬럼을 두고 트리거로 갱신하는 방식을 검토할 수 있다. 다만 정합성 관리 비용이 생기므로 실제 성능 문제가 확인된 후에 도입하는 편이 낫다.

### 7.3 링크 기반 접근의 보안 수준

`share_code`를 아는 사람은 누구나 조회·수정·삭제할 수 있다. 8~32자 영숫자라 무차별 대입은 현실적으로 어렵지만, 링크가 유출되면 방어 수단이 없다. 필요해지면 조회 전용 코드와 편집 코드를 분리하는 방식을 고려할 수 있다.

### 7.4 감사 로그 없음

누가 언제 어떤 결제 내역을 수정했는지 추적할 수 없다. 여러 명이 같은 방을 편집하는 구조라 분쟁 소지가 있다면 `receipt_history` 테이블 추가를 검토한다.

### 7.5 증빙 이미지 1장 제한

`receipt.image_file_id`가 단일 FK다. 영수증 여러 장을 첨부하려면 `receipt_image` 조인 테이블로 분리해야 한다. 현재 기획서 기준으로는 1장이면 충분하다.
