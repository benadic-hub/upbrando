from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


user_role = postgresql.ENUM("SUPERADMIN", "ADMIN", "EMPLOYEE", "AI_AGENT", name="user_role", create_type=False)
invite_role = postgresql.ENUM("SUPERADMIN", "ADMIN", "EMPLOYEE", "AI_AGENT", name="invite_role", create_type=False)
task_status = postgresql.ENUM("TODO", "IN_PROGRESS", "DONE", "BLOCKED", name="task_status", create_type=False)
ticket_status = postgresql.ENUM("OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED", name="ticket_status", create_type=False)
break_kind = postgresql.ENUM("BREAK", "LUNCH", name="break_kind", create_type=False)


def _tenant_col() -> sa.Column:
    return sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default=sa.text("'default'"))


def upgrade() -> None:
    bind = op.get_bind()
    user_role.create(bind, checkfirst=True)
    invite_role.create(bind, checkfirst=True)
    task_status.create(bind, checkfirst=True)
    ticket_status.create(bind, checkfirst=True)
    break_kind.create(bind, checkfirst=True)

    op.create_table(
        "departments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        _tenant_col(),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False, server_default=sa.text("''")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", "name", name="uq_departments_tenant_name"),
    )
    op.create_index("ix_departments_tenant_id", "departments", ["tenant_id"])

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        _tenant_col(),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("google_sub", sa.String(length=255), nullable=True),
        sa.Column("password_hash", sa.String(length=500), nullable=True),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("manager_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("work_start_time", sa.Time(), nullable=False, server_default=sa.text("'09:00:00'")),
        sa.Column("work_end_time", sa.Time(), nullable=False, server_default=sa.text("'18:00:00'")),
        sa.Column("break_minutes", sa.Integer(), nullable=False, server_default=sa.text("15")),
        sa.Column("lunch_minutes", sa.Integer(), nullable=False, server_default=sa.text("60")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])

    op.create_table(
        "agent_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        _tenant_col(),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("tools_allowed", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_agent_profiles_tenant_id", "agent_profiles", ["tenant_id"])

    op.create_table(
        "invites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        _tenant_col(),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("role", invite_role, nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("manager_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("tools_allowed", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("invited_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_invites_tenant_id", "invites", ["tenant_id"])

    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        _tenant_col(),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_refresh_tokens_tenant_id", "refresh_tokens", ["tenant_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        _tenant_col(),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("target_type", sa.String(length=80), nullable=False, server_default=sa.text("''")),
        sa.Column("target_id", sa.String(length=80), nullable=False, server_default=sa.text("''")),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_audit_logs_tenant_id", "audit_logs", ["tenant_id"])

    op.create_table(
        "time_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        _tenant_col(),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("check_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("check_out_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_worked_minutes", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("ot_minutes", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("break_minutes", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("lunch_minutes", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", "user_id", "work_date", name="uq_time_entries_tenant_user_date"),
    )
    op.create_index("ix_time_entries_tenant_id", "time_entries", ["tenant_id"])

    op.create_table(
        "time_break_windows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        _tenant_col(),
        sa.Column("time_entry_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("time_entries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", break_kind, nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_time_break_windows_tenant_id", "time_break_windows", ["tenant_id"])

    op.create_table(
        "agent_heartbeats",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        _tenant_col(),
        sa.Column("agent_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("activity", sa.String(length=500), nullable=False, server_default=sa.text("''")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_agent_heartbeats_tenant_id", "agent_heartbeats", ["tenant_id"])

    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        _tenant_col(),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("status", task_status, nullable=False, server_default=sa.text("'TODO'")),
        sa.Column("assignee_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_tasks_tenant_id", "tasks", ["tenant_id"])

    op.create_table(
        "helpdesk_tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        _tenant_col(),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("status", ticket_status, nullable=False, server_default=sa.text("'OPEN'")),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assigned_to_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_helpdesk_tickets_tenant_id", "helpdesk_tickets", ["tenant_id"])

    op.create_table(
        "chat_threads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        _tenant_col(),
        sa.Column("is_dm", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_chat_threads_tenant_id", "chat_threads", ["tenant_id"])

    op.create_table(
        "chat_thread_participants",
        _tenant_col(),
        sa.Column("thread_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chat_threads.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("last_read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_chat_thread_participants_tenant_id", "chat_thread_participants", ["tenant_id"])

    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        _tenant_col(),
        sa.Column("thread_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chat_threads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sender_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_chat_messages_tenant_id", "chat_messages", ["tenant_id"])

    op.create_table(
        "announcements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        _tenant_col(),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_announcements_tenant_id", "announcements", ["tenant_id"])

    op.create_table(
        "announcement_reads",
        _tenant_col(),
        sa.Column("announcement_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("announcements.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_announcement_reads_tenant_id", "announcement_reads", ["tenant_id"])

    op.create_table(
        "knowledge_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        _tenant_col(),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False, server_default=sa.text("''")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", "name", name="uq_knowledge_category_tenant_name"),
    )
    op.create_index("ix_knowledge_categories_tenant_id", "knowledge_categories", ["tenant_id"])

    op.create_table(
        "knowledge_articles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        _tenant_col(),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("knowledge_categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_knowledge_articles_tenant_id", "knowledge_articles", ["tenant_id"])

    op.create_table(
        "form_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        _tenant_col(),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("fields_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_form_templates_tenant_id", "form_templates", ["tenant_id"])

    op.create_table(
        "form_submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        _tenant_col(),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("form_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("submitted_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("answers_encrypted", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_form_submissions_tenant_id", "form_submissions", ["tenant_id"])

    op.create_table(
        "attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        _tenant_col(),
        sa.Column("owner_type", sa.String(length=80), nullable=False, server_default=sa.text("''")),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("filename", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("s3_key", sa.String(length=800), nullable=False, unique=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_attachments_tenant_id", "attachments", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_attachments_tenant_id", table_name="attachments")
    op.drop_table("attachments")

    op.drop_index("ix_form_submissions_tenant_id", table_name="form_submissions")
    op.drop_table("form_submissions")

    op.drop_index("ix_form_templates_tenant_id", table_name="form_templates")
    op.drop_table("form_templates")

    op.drop_index("ix_knowledge_articles_tenant_id", table_name="knowledge_articles")
    op.drop_table("knowledge_articles")

    op.drop_index("ix_knowledge_categories_tenant_id", table_name="knowledge_categories")
    op.drop_table("knowledge_categories")

    op.drop_index("ix_announcement_reads_tenant_id", table_name="announcement_reads")
    op.drop_table("announcement_reads")

    op.drop_index("ix_announcements_tenant_id", table_name="announcements")
    op.drop_table("announcements")

    op.drop_index("ix_chat_messages_tenant_id", table_name="chat_messages")
    op.drop_table("chat_messages")

    op.drop_index("ix_chat_thread_participants_tenant_id", table_name="chat_thread_participants")
    op.drop_table("chat_thread_participants")

    op.drop_index("ix_chat_threads_tenant_id", table_name="chat_threads")
    op.drop_table("chat_threads")

    op.drop_index("ix_helpdesk_tickets_tenant_id", table_name="helpdesk_tickets")
    op.drop_table("helpdesk_tickets")

    op.drop_index("ix_tasks_tenant_id", table_name="tasks")
    op.drop_table("tasks")

    op.drop_index("ix_agent_heartbeats_tenant_id", table_name="agent_heartbeats")
    op.drop_table("agent_heartbeats")

    op.drop_index("ix_time_break_windows_tenant_id", table_name="time_break_windows")
    op.drop_table("time_break_windows")

    op.drop_index("ix_time_entries_tenant_id", table_name="time_entries")
    op.drop_table("time_entries")

    op.drop_index("ix_audit_logs_tenant_id", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_refresh_tokens_tenant_id", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")

    op.drop_index("ix_invites_tenant_id", table_name="invites")
    op.drop_table("invites")

    op.drop_index("ix_agent_profiles_tenant_id", table_name="agent_profiles")
    op.drop_table("agent_profiles")

    op.drop_index("ix_users_tenant_id", table_name="users")
    op.drop_table("users")

    op.drop_index("ix_departments_tenant_id", table_name="departments")
    op.drop_table("departments")

    bind = op.get_bind()
    break_kind.drop(bind, checkfirst=True)
    ticket_status.drop(bind, checkfirst=True)
    task_status.drop(bind, checkfirst=True)
    invite_role.drop(bind, checkfirst=True)
    user_role.drop(bind, checkfirst=True)
