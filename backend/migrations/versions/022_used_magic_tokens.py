"""Add used_magic_tokens table for single-use magic link enforcement (F-012).

Revision ID: 022
Revises: 021
Create Date: 2026-03-25
"""

from alembic import op
import sqlalchemy as sa


revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "used_magic_tokens",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column(
            "used_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_used_magic_tokens_token_hash",
        "used_magic_tokens",
        ["token_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_used_magic_tokens_token_hash",
        table_name="used_magic_tokens",
    )
    op.drop_table("used_magic_tokens")
