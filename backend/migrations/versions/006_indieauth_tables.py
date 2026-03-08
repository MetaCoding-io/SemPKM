"""Create IndieAuth authorization codes and tokens tables.

Revision ID: 006
Revises: 005
Create Date: 2026-03-08
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "indieauth_codes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("client_id", sa.String(2048), nullable=False),
        sa.Column("redirect_uri", sa.String(2048), nullable=False),
        sa.Column("scope", sa.String(512), nullable=False),
        sa.Column("code_challenge", sa.String(128), nullable=False),
        sa.Column("code_challenge_method", sa.String(10), nullable=False, server_default="S256"),
        sa.Column("state", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_indieauth_codes_code_hash", "indieauth_codes", ["code_hash"], unique=True)
    op.create_index("ix_indieauth_codes_user_id", "indieauth_codes", ["user_id"])

    op.create_table(
        "indieauth_tokens",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("refresh_token_hash", sa.String(64), nullable=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("client_id", sa.String(2048), nullable=False),
        sa.Column("scope", sa.String(512), nullable=False),
        sa.Column("client_name", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("refresh_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_indieauth_tokens_token_hash", "indieauth_tokens", ["token_hash"], unique=True)
    op.create_index(
        "ix_indieauth_tokens_refresh_token_hash",
        "indieauth_tokens",
        ["refresh_token_hash"],
        unique=True,
    )
    op.create_index("ix_indieauth_tokens_user_id", "indieauth_tokens", ["user_id"])


def downgrade() -> None:
    op.drop_table("indieauth_tokens")
    op.drop_table("indieauth_codes")
