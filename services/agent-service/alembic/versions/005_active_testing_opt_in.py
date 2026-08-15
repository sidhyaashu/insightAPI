"""005_active_testing_opt_in — Add active_testing_opt_in to verified_domains table.

Revision ID: 005_active_testing_opt_in
Revises: 004_security_v2
Create Date: 2026-08-15
"""
from alembic import op
import sqlalchemy as sa

revision = "005_active_testing_opt_in"
down_revision = "004_security_v2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "verified_domains",
        sa.Column(
            "active_testing_opt_in",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="Explicit user opt-in allowing active security testing probes on this domain.",
        ),
    )


def downgrade() -> None:
    op.drop_column("verified_domains", "active_testing_opt_in")
