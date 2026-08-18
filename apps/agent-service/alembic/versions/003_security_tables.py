"""003_security_tables — Add security_test_patterns and security_findings tables.

Revision ID: 003_security_tables
Revises: 002_llm_usage
Create Date: 2026-08-15
"""
from alembic import op
import sqlalchemy as sa

revision = "003_security_tables"
down_revision = "002_llm_usage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. security_test_patterns — cross-target generalizable pattern cache
    op.create_table(
        "security_test_patterns",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column(
            "endpoint_signature", sa.String(length=64), nullable=False,
            comment="SHA-256 of (method+param_types+param_names+auth+schema_shape)"
        ),
        sa.Column(
            "vuln_class", sa.String(length=32), nullable=False,
            comment="idor|injection|auth_bypass|mass_assignment|rate_limit_bypass|ssrf_via_param|other"
        ),
        sa.Column("test_strategy", sa.JSON(), nullable=False),
        sa.Column(
            "outcome", sa.String(length=32), nullable=False,
            comment="vulnerable|not_vulnerable|inconclusive"
        ),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("occurrences", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "reasoning_trace", sa.Text(), nullable=True,
            comment="LLM chain-of-thought. Stored for audit. NOT re-sent on cache hit."
        ),
        sa.Column(
            "status", sa.String(length=32), nullable=False, server_default="needs_review",
            comment="needs_review|learned|deprecated"
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("endpoint_signature", name="uq_security_pattern_signature"),
    )
    op.create_index(
        "ix_security_test_patterns_signature",
        "security_test_patterns",
        ["endpoint_signature"],
    )
    op.create_index(
        "ix_security_test_patterns_status_confidence",
        "security_test_patterns",
        ["status", "confidence"],
    )
    op.create_index(
        "ix_security_test_patterns_vuln_class",
        "security_test_patterns",
        ["vuln_class"],
    )

    # 2. security_findings — one row per confirmed vulnerability per crawl
    op.create_table(
        "security_findings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("crawl_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column(
            "pattern_id", sa.String(length=36), nullable=False,
            comment="FK to security_test_patterns.id"
        ),
        sa.Column("endpoint_signature", sa.String(length=64), nullable=False),
        sa.Column("vuln_class", sa.String(length=32), nullable=False),
        sa.Column("endpoint_route", sa.Text(), nullable=True),
        sa.Column("method", sa.String(length=16), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=True),
        sa.Column(
            "severity", sa.String(length=16), nullable=False, server_default="medium",
            comment="info|low|medium|high|critical"
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_security_findings_crawl_id", "security_findings", ["crawl_id"])
    op.create_index("ix_security_findings_user_id", "security_findings", ["user_id"])
    op.create_index("ix_security_findings_pattern_id", "security_findings", ["pattern_id"])
    op.create_index(
        "ix_security_findings_signature", "security_findings", ["endpoint_signature"]
    )


def downgrade() -> None:
    op.drop_table("security_findings")
    op.drop_table("security_test_patterns")
