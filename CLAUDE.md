# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**정산정산 (jungsanjungsan)** — backend for a travel expense-settlement app. A trip gets a "정산방" (settlement room); members log receipts during the trip; at the end the room is settled and a snapshot of who-owes-whom is produced. No authentication — anyone holding a room's `share_code` link can read/write it.

The codebase is currently a minimal FastAPI scaffold (only a `users` module exists, from the initial project setup). The real domain model — `room`, `member`, `receipt`, `settlement`, `settlement_entry`, `file_object` — is designed but not yet implemented; see **Domain design docs** below before building it.

## Commands

Package/env manager is `uv`; Python 3.12 (`.python-version`).

```bash
# install deps into .venv
uv sync

# apply DB migrations
uv run alembic upgrade head

# run dev server (auto-reload)
uv run fastapi dev

# run prod server
uv run fastapi run

# after changing SQLAlchemy models, generate + apply a migration
uv run alembic revision --autogenerate -m "message"
uv run alembic upgrade head
```

There is no configured lint, format, or test tooling in this repo (`pyproject.toml` has no dev-dependency group for it) — don't assume `pytest`/`ruff`/`black` exist unless they're added.

### Environment

`.env` (loaded by `src/config.py` via `pydantic-settings`) requires:

```
DATABASE_URL=postgresql+psycopg://{user}:{password}@localhost:5432/{db}
JWT_SECRET={secret}
```

Requires a local PostgreSQL instance. `alembic/env.py` pulls `DATABASE_URL` from the same `Settings` object, so app and migrations always target the same database.

## Architecture

FastAPI app assembled in `main.py`, which imports and includes each feature module's router. Feature modules live under `src/<feature>/` and follow a fixed layering (NestJS-equivalent noted per the project README):

| Layer | File | Role |
|---|---|---|
| `router.py` | HTTP endpoints, `APIRouter` per feature, `Depends(get_db)` for the session | Controller |
| `service.py` | business logic, raises plain `ValueError` for domain errors (not yet mapped to HTTP error responses) | Service |
| `repository.py` | DB queries/writes, takes a `Session` explicitly, returns ORM models | Repository |
| `model.py` | SQLAlchemy `Mapped`/`mapped_column` models, `Base` from `src/core/database.py` | Entity |
| `schema.py` | Pydantic request/response DTOs (`model_config = {"from_attributes": True}` for ORM responses) | DTO |

`src/core/database.py` owns the SQLAlchemy `engine`, `SessionLocal`, the declarative `Base`, and the `get_db()` FastAPI dependency (session-per-request, closed in a `finally`). Any new model must import `Base` from here and be imported into `alembic/env.py` (see how `src/users/model.py` is wired) so autogenerate can see it.

`src/config.py` defines the single `Settings` (pydantic-settings) object used everywhere config is needed — import `settings` from there rather than reading env vars directly.

Alembic runs in "online" mode against a live connection (`alembic/env.py`); offline mode is also wired but unused in the documented workflow.

## Domain design docs (`context/`)

This directory holds the target design for the full app (ahead of implementation) and is the source of truth when building out `room`/`member`/`receipt`/`settlement`:

- `context/DB_MODEL.md` — full schema spec: tables, constraints, indexes, triggers (`guard_room_settled` blocks writes on settled rooms, `guard_member_has_receipts` blocks deleting members with receipts), views (`room_dashboard_view`, `settlement_guide_view`), and settlement math (remainder allocation to the treasurer, `sum(balance_amount) = 0` invariant that must be verified in application code since it can't be a SQL `CHECK`).
- `context/api/` — per-endpoint API spec (rooms/members/receipts/settlement/files), including the shared error envelope, cursor-pagination format, and PATCH null-vs-omitted-field semantics.
- `context/SCRREN_PLAN.md` — frontend sitemap/screen flow; useful for understanding what each endpoint is called from.
- `context/DESIGN.md` — visual design system reference for the frontend; not applicable to backend work.

Key domain rules worth knowing before implementing:
- No auth model — `share_code` (not the internal `uuid` PK) is the public identifier and is what API paths use; the PK must never appear in responses.
- `member` and `receipt` are soft-deleted (`deleted_at`); `room` and `file_object` are hard-deleted.
- Settlement uses a hub-and-spoke model through a single `is_treasurer` member per room, not N:N transfers.
- Once a room is `SETTLED`, its members/receipts become read-only (enforced by DB trigger, should also be checked in the service layer to return the correct API error code instead of a generic constraint violation).
