from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002_pilot_extensions"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


employee_type = postgresql.ENUM("HUMAN", "AGENT", name="employee_type", create_type=False)


def _tenant_col() -> sa.Column:
    return sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default=sa.text("'default'"))


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_enum e
                JOIN pg_type t ON t.oid = e.enumtypid
                WHERE t.typname = 'user_role' AND e.enumlabel = 'HOD'
            ) THEN
                ALTER TYPE user_role ADD VALUE 'HOD';
            END IF;
        END$$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_enum e
                JOIN pg_type t ON t.oid = e.enumtypid
                WHERE t.typname = 'invite_role' AND e.enumlabel = 'HOD'
            ) THEN
                ALTER TYPE invite_role ADD VALUE 'HOD';
            END IF;
        END$$;
        """
    )

    op.create_table(
        "tenants",
        sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.add_column("departments", sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_departments_parent_id_departments",
        "departments",
        "departments",
        ["parent_id"],
        ["id"],
        ondelete="SET NULL",
    )

    bind = op.get_bind()
    employee_type.create(bind, checkfirst=True)
    op.add_column(
        "users",
        sa.Column("employee_type", employee_type, nullable=False, server_default=sa.text("'HUMAN'")),
    )

    op.add_column("time_entries", sa.Column("source", sa.String(length=40), nullable=False, server_default=sa.text("'api'")))
    op.add_column("time_entries", sa.Column("notes", sa.Text(), nullable=True))

    op.create_table(
        "task_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        _tenant_col(),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_task_comments_tenant_id", "task_comments", ["tenant_id"])

    op.add_column("chat_threads", sa.Column("title", sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column("chat_threads", "title")

    op.drop_index("ix_task_comments_tenant_id", table_name="task_comments")
    op.drop_table("task_comments")

    op.drop_column("time_entries", "notes")
    op.drop_column("time_entries", "source")

    op.drop_column("users", "employee_type")

    op.drop_constraint("fk_departments_parent_id_departments", "departments", type_="foreignkey")
    op.drop_column("departments", "parent_id")

    op.drop_table("tenants")

    bind = op.get_bind()
    employee_type.drop(bind, checkfirst=True)
