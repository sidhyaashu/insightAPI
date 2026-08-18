"""004_security_v2 — Upgrade security tables with V2 schema.

Adds:
- security_test_patterns: is_destructive, distinct_target_count, seen_domains,
  last_human_reviewed_at; raises OCCURRENCES_THRESHOLD contract to 20/15.
- security_findings: ran_via_cache
- security_approvals: new table for single-use human-approval gate

Revision ID: 004_security_v2
Revises: 003_security_tables
Create Date: 2026-08-15
"""
from alembic import op
import sqlalchemy as sa

revision = "004_security_v2"
down_revision = "003_security_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. security_test_patterns — V2 additions ──────────────────────────────
    op.add_column(
        "security_test_patterns",
        sa.Column(
            "is_destructive", sa.Boolean(), nullable=False, server_default="false",
            comment="True=can modify/delete/trigger side-effects. Hard-blocks auto-promotion."
        ),
    )
    op.add_column(
        "security_test_patterns",
        sa.Column(
            "distinct_target_count", sa.Integer(), nullable=False, server_default="1",
            comment="Count of different domains confirmed. Promotion requires >=15."
        ),
    )
    op.add_column(
        "security_test_patterns",
        sa.Column(
            "seen_domains", sa.JSON(), nullable=True,
            comment="JSON array of domain strings counted for distinct_target_count."
        ),
    )
    op.add_column(
        "security_test_patterns",
        sa.Column(
            "last_human_reviewed_at", sa.DateTime(timezone=True), nullable=True,
            comment="When a human last reviewed/approved a run using this pattern."
        ),
    )

    # Composite index for promotion eligibility queries
    op.create_index(
        "ix_security_patterns_promotion_eligibility",
        "security_test_patterns",
        ["status", "is_destructive", "distinct_target_count", "occurrences"],
    )

    # ── 2. security_findings — add ran_via_cache ──────────────────────────────
    op.add_column(
        "security_findings",
        sa.Column(
            "ran_via_cache", sa.Boolean(), nullable=False, server_default="false",
            comment="True when finding came from cached pattern replay (no LLM cost)."
        ),
    )

    # ── 3. security_approvals — single-use human-approval gate ───────────────
    op.create_table(
        "security_approvals",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column(
            "pattern_id", sa.String(length=36), nullable=False,
            comment="FK to security_test_patterns.id (soft reference)"
        ),
        sa.Column("crawl_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("endpoint_route", sa.Text(), nullable=True),
        sa.Column("method", sa.String(length=16), nullable=True),
        sa.Column("target_domain", sa.String(length=256), nullable=True),
        sa.Column("test_strategy_snapshot", sa.JSON(), nullable=True),
        sa.Column(
            "status", sa.String(length=32), nullable=False, server_default="pending",
            comment="pending|approved|rejected|executed"
        ),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.String(length=36), nullable=True),
        sa.Column("execution_result", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_security_approvals_pattern_id", "security_approvals", ["pattern_id"])
    op.create_index("ix_security_approvals_crawl_id", "security_approvals", ["crawl_id"])
    op.create_index("ix_security_approvals_user_id", "security_approvals", ["user_id"])
    op.create_index("ix_security_approvals_status", "security_approvals", ["status"])


def downgrade() -> None:
    op.drop_table("security_approvals")
    op.drop_column("security_findings", "ran_via_cache")
    op.drop_index("ix_security_patterns_promotion_eligibility", "security_test_patterns")
    op.drop_column("security_test_patterns", "last_human_reviewed_at")
    op.drop_column("security_test_patterns", "seen_domains")
    op.drop_column("security_test_patterns", "distinct_target_count")
    op.drop_column("security_test_patterns", "is_destructive")
