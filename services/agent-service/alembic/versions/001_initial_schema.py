"""Initial baseline schema migration

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-08-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. crawl_sessions
    op.create_table(
        "crawl_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("user_tier", sa.String(length=32), nullable=False, server_default="FREE"),
        sa.Column("target_url", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="running"),
        sa.Column("max_pages", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("goal", sa.Text(), nullable=True),
        sa.Column("captured_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("openapi_spec", sa.JSON(), nullable=True),
        sa.Column("postman_collection", sa.JSON(), nullable=True),
        sa.Column("markdown_docs", sa.Text(), nullable=True),
        sa.Column("reviewed_endpoints", sa.JSON(), nullable=True),
        sa.Column("action_traces", sa.JSON(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("llm_metrics_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crawl_sessions_user_id", "crawl_sessions", ["user_id"])

    # 2. crawl_snapshots (API Drift Detection)
    op.create_table(
        "crawl_snapshots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("crawl_id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("endpoint_key", sa.String(length=512), nullable=False),
        sa.Column("schema_json", sa.JSON(), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=False, server_default="200"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("crawl_id", "endpoint_key", name="uq_snapshot_crawl_endpoint"),
    )
    op.create_index("ix_crawl_snapshots_crawl_id", "crawl_snapshots", ["crawl_id"])
    op.create_index("ix_crawl_snapshots_project_id", "crawl_snapshots", ["project_id"])
    op.create_index("ix_snapshot_project_crawl", "crawl_snapshots", ["project_id", "crawl_id"])

    # 3. verified_domains & tos_acceptances
    op.create_table(
        "verified_domains",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("domain", sa.String(length=256), nullable=False),
        sa.Column("verification_token", sa.String(length=128), nullable=False),
        sa.Column("verification_method", sa.String(length=32), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_verified_domains_domain", "verified_domains", ["domain"])
    op.create_index("ix_verified_domains_user_id", "verified_domains", ["user_id"])

    op.create_table(
        "tos_acceptances",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("domain", sa.String(length=256), nullable=False),
        sa.Column("target_url", sa.Text(), nullable=False),
        sa.Column("user_ip", sa.String(length=64), nullable=False, server_default="unknown"),
        sa.Column("tos_version", sa.String(length=32), nullable=False, server_default="v1.0"),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tos_acceptances_domain", "tos_acceptances", ["domain"])
    op.create_index("ix_tos_acceptances_user_id", "tos_acceptances", ["user_id"])

    # 4. auth_profiles
    op.create_table(
        "auth_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False, server_default="default"),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("target_domain", sa.String(length=255), nullable=False),
        sa.Column("login_url", sa.Text(), nullable=False),
        sa.Column("auth_type", sa.String(length=32), nullable=False, server_default="form"),
        sa.Column("encrypted_credentials", sa.Text(), nullable=False),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_test_status", sa.String(length=32), nullable=True),
        sa.Column("last_test_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_auth_profiles_target_domain", "auth_profiles", ["target_domain"])
    op.create_index("ix_auth_profiles_user_id", "auth_profiles", ["user_id"])
    op.create_index("ix_auth_profiles_project_id", "auth_profiles", ["project_id"])

    # 5. audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=False, server_default="default"),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=128), nullable=True),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_project_id", "audit_logs", ["project_id"])
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_target_id", "audit_logs", ["target_id"])
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])

    # 6. chat_messages
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])
    op.create_index("ix_chat_messages_user_id", "chat_messages", ["user_id"])


def downgrade() -> None:
    op.drop_table("chat_messages")
    op.drop_table("audit_logs")
    op.drop_table("auth_profiles")
    op.drop_table("tos_acceptances")
    op.drop_table("verified_domains")
    op.drop_table("crawl_snapshots")
    op.drop_table("crawl_sessions")
