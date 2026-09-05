"""add trigger functions and dashboard views

Revision ID: 839f4736d7ff
Revises: e15394e0388c
Create Date: 2026-09-05 14:50:32.503370

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '839f4736d7ff'
down_revision: Union[str, Sequence[str], None] = 'e15394e0388c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # DB_MODEL.md 3.1 — updated_at 자동 갱신
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    for table in ("room", "member", "receipt"):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_set_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION set_updated_at();
            """
        )

    # DB_MODEL.md 3.2 — 정산 완료된 방의 member/receipt를 읽기 전용으로 만든다
    op.execute(
        """
        CREATE OR REPLACE FUNCTION guard_room_settled() RETURNS trigger AS $$
        DECLARE
            target_room_id uuid;
            room_status_value text;
        BEGIN
            target_room_id := COALESCE(NEW.room_id, OLD.room_id);
            SELECT status INTO room_status_value FROM room WHERE id = target_room_id;

            IF room_status_value = 'SETTLED' THEN
                RAISE EXCEPTION '정산이 완료된 방은 수정할 수 없습니다 (room_id=%)', target_room_id
                    USING ERRCODE = 'check_violation';
            END IF;

            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    for table in ("member", "receipt"):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_guard_room_settled
            BEFORE INSERT OR UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION guard_room_settled();
            """
        )

    # DB_MODEL.md 3.3 — 결제 내역이 있는 멤버는 소프트 삭제 금지
    op.execute(
        """
        CREATE OR REPLACE FUNCTION guard_member_has_receipts() RETURNS trigger AS $$
        DECLARE
            active_receipt_count integer;
        BEGIN
            IF OLD.deleted_at IS NULL AND NEW.deleted_at IS NOT NULL THEN
                SELECT count(*) INTO active_receipt_count
                FROM receipt
                WHERE payer_member_id = OLD.id AND deleted_at IS NULL;

                IF active_receipt_count > 0 THEN
                    RAISE EXCEPTION '결제 내역이 있는 멤버는 삭제할 수 없습니다 (member=%)', OLD.id
                        USING ERRCODE = 'check_violation';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_member_guard_has_receipts
        BEFORE UPDATE ON member
        FOR EACH ROW EXECUTE FUNCTION guard_member_has_receipts();
        """
    )

    # DB_MODEL.md 4.1 — /room/{id} 대시보드 한 번에 조회
    op.execute(
        """
        CREATE VIEW room_dashboard_view AS
        SELECT
            r.id AS room_id,
            r.share_code,
            r.title,
            r.status,
            r.total_budget,
            r.thumbnail_file_id,
            r.created_at,
            r.settled_at,
            COALESCE(mem.member_count, 0) AS member_count,
            CASE WHEN COALESCE(mem.member_count, 0) = 0 THEN 0
                 ELSE r.total_budget / mem.member_count
            END AS budget_per_person,
            COALESCE(rec.total_paid, 0) AS total_paid,
            COALESCE(rec.receipt_count, 0) AS receipt_count,
            CASE WHEN r.total_budget = 0 THEN NULL
                 ELSE round(COALESCE(rec.total_paid, 0)::numeric / r.total_budget * 100, 1)
            END AS usage_percent
        FROM room r
        LEFT JOIN LATERAL (
            SELECT count(*) AS member_count
            FROM member m
            WHERE m.room_id = r.id AND m.deleted_at IS NULL
        ) mem ON true
        LEFT JOIN LATERAL (
            SELECT sum(amount) AS total_paid, count(*) AS receipt_count
            FROM receipt rc
            WHERE rc.room_id = r.id AND rc.deleted_at IS NULL
        ) rec ON true;
        """
    )

    # DB_MODEL.md 4.2 — /room/{id}/result 정산 결과 화면용
    op.execute(
        """
        CREATE VIEW settlement_guide_view AS
        SELECT
            s.id AS settlement_id,
            s.room_id,
            s.room_title,
            s.budget_amount,
            s.period_start_at,
            s.period_end_at,
            s.total_amount,
            s.member_count,
            s.per_person_amount,
            s.receipt_count,
            s.created_at,
            CASE WHEN s.budget_amount = 0 THEN NULL
                 ELSE round((s.total_amount - s.budget_amount)::numeric / s.budget_amount * 100, 1)
            END AS budget_diff_percent,
            e.id AS entry_id,
            e.member_id,
            e.member_name,
            e.is_treasurer,
            e.paid_amount,
            e.share_amount,
            e.balance_amount,
            CASE WHEN e.balance_amount > 0 THEN 'RECEIVE'
                 WHEN e.balance_amount < 0 THEN 'SEND'
                 ELSE 'NONE'
            END AS direction
        FROM settlement s
        JOIN settlement_entry e ON e.settlement_id = s.id;
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP VIEW IF EXISTS settlement_guide_view")
    op.execute("DROP VIEW IF EXISTS room_dashboard_view")

    op.execute("DROP TRIGGER IF EXISTS trg_member_guard_has_receipts ON member")
    op.execute("DROP FUNCTION IF EXISTS guard_member_has_receipts()")

    op.execute("DROP TRIGGER IF EXISTS trg_receipt_guard_room_settled ON receipt")
    op.execute("DROP TRIGGER IF EXISTS trg_member_guard_room_settled ON member")
    op.execute("DROP FUNCTION IF EXISTS guard_room_settled()")

    op.execute("DROP TRIGGER IF EXISTS trg_receipt_set_updated_at ON receipt")
    op.execute("DROP TRIGGER IF EXISTS trg_member_set_updated_at ON member")
    op.execute("DROP TRIGGER IF EXISTS trg_room_set_updated_at ON room")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")
