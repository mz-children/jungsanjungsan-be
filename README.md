## 사전 설치

- python
- pyenv
- uv
- postgrsql

## 환경변수 세팅

### .env

```bash
DATABASE_URL=postgresql+psycopg://{DB계정이름}:{비밀번호}@localhost:5432/{데이터베이스이름}
JWT_SECRET={토큰시크릿}
```

## 설치

```bash
# 파이썬 버전 적용
pyenv local 3.12

# 가상환경 생성 + 의존성 설치
uv sync

# DB 마이그레이션 적용
uv run alembic upgrade head
```

## 실행

```bash
# 개발모드 실행
uv run fastapi dev

# 프로덕션모드 실행
uv run fastapi run
```

## 디렉토리 설명

| 디렉토리       | 역할                  | NestJS 비교        |
| -------------- | --------------------- | ------------------ |
| `routers`      | HTTP API endpoint     | Controller         |
| `services`     | 비즈니스 로직         | Service            |
| `repositories` | DB 조회/수정          | Repository         |
| `models`       | SQLAlchemy DB 모델    | Entity             |
| `schemas`      | Request/Response DTO  | DTO                |
| `core`         | 설정, DB, 공통 인프라 | Config/Database 등 |

## DB 변경사항 발생시 마이그레이션 방법

```bash
# DB 마이그레이션 생성
uv run alembic revision --autogenerate -m "migration commit message"

# DB 마이그레이션 적용
uv run alembic upgrade head
```
