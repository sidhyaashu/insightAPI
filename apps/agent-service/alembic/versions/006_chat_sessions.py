"""006_chat_sessions — add chat_sessions table for DB-first session lifecycle.

Revision ID: 006_chat_sessions
Revises: 005_active_testing_opt_in
Create Date: 2026-08-15
"""
from alembic import op
import sqlalchemy as sa

revision = "006_chat_sessions"
down_revision = "005_active_testing_opt_in"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create chat_sessions table
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False, server_default="New Conversation"),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_sessions_user_id", "chat_sessions", ["user_id"])
    op.create_index("ix_chat_sessions_updated_at", "chat_sessions", ["updated_at"])


def downgrade() -> None:
    op.drop_index("ix_chat_sessions_updated_at", table_name="chat_sessions")
    op.drop_index("ix_chat_sessions_user_id", table_name="chat_sessions")
    op.drop_table("chat_sessions")
