"""Add scope column to api_tokens table (F-016).

Revision ID: 023
Revises: 022
Create Date: 2026-03-25
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "api_tokens",
        sa.Column("scope", sa.String(1024), server_default="*", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("api_tokens", "scope")
