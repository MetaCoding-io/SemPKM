"""Add personas table for workspace persona management.

Revision ID: 013
Revises: 012
Create Date: 2026-03-17
"""

from alembic import op
import sqlalchemy as sa


revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "personas",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("layout_json", sa.Text(), server_default="{}", nullable=False),
        sa.Column(
            "sidebar_positions_json", sa.Text(), server_default="{}", nullable=False
        ),
        sa.Column(
            "explorer_mode", sa.String(50), server_default="by-type", nullable=False
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )


def downgrade() -> None:
    op.drop_table("personas")
