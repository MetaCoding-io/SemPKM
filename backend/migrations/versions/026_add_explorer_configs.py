"""Add explorer_configs table for named explorer panel configurations.

Stores user-created and built-in preset explorer configurations with
group_by, sort_by, type_filter settings as JSON.

Revision ID: 026
Revises: 025
Create Date: 2026-04-05
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "explorer_configs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("config_json", sa.Text(), server_default="{}", nullable=False),
        sa.Column("is_preset", sa.Boolean(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("explorer_configs")
