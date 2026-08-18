"""Initial baseline schema migration for core-service

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-08-15

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=256), nullable=False),
        sa.Column("hashed_password", sa.String(length=256), nullable=True),
        sa.Column("login_method", sa.String(length=32), nullable=False, server_default="email"),
        sa.Column("oauth_provider", sa.String(length=32), nullable=True),
        sa.Column("oauth_sub", sa.String(length=256), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("verification_token", sa.String(length=256), nullable=True),
        sa.Column("verification_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_reset_token", sa.String(length=256), nullable=True),
        sa.Column("password_reset_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("name", sa.String(length=256), nullable=True),
        sa.Column("avatar_url", sa.String(length=512), nullable=True),
        sa.Column("tier", sa.String(length=32), nullable=False, server_default="FREE"),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="user"),
        sa.Column("stripe_customer_id", sa.String(length=256), nullable=True),
        sa.Column("allow_overage", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_oauth_sub", "users", ["oauth_sub"])
    op.create_index("ix_users_verification_token", "users", ["verification_token"])
    op.create_index("ix_users_password_reset_token", "users", ["password_reset_token"])

    # 2. subscriptions
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("stripe_subscription_id", sa.String(length=256), nullable=True),
        sa.Column("stripe_price_id", sa.String(length=256), nullable=True),
        sa.Column("tier", sa.String(length=32), nullable=False, server_default="FREE"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stripe_subscription_id"),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])

    # 3. api_keys
    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column(
            "user_id", sa.String(length=36), nullable=False,
        ),
        sa.Column("name", sa.String(length=128), nullable=False, server_default="CLI / SDK Key"),
        sa.Column("key_prefix", sa.String(length=16), nullable=False),
        sa.Column("hashed_key", sa.String(length=256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hashed_key"),
    )
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])
    op.create_index("ix_api_keys_hashed_key", "api_keys", ["hashed_key"], unique=True)


def downgrade() -> None:
    op.drop_table("api_keys")
    op.drop_table("subscriptions")
    op.drop_table("users")
