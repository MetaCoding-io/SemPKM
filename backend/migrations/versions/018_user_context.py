"""Add user_context table for context awareness.

Revision ID: 018
Revises: 017
Create Date: 2026-03-23
"""

from alembic import op
import sqlalchemy as sa


revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_context",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("location_zone", sa.String(100), nullable=True),
        sa.Column("activity", sa.String(50), nullable=True),
        sa.Column("time_period", sa.String(50), nullable=True),
        sa.Column("calendar_event", sa.String(500), nullable=True),
        sa.Column(
            "calendar_busy",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("device_id", sa.String(100), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_user_context_user_id", "user_context", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_user_context_user_id", table_name="user_context")
    op.drop_table("user_context")
