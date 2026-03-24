"""Add context_rules table and manual_override to user_context.

Revision ID: 019
Revises: 018
Create Date: 2026-03-23
"""

from alembic import op
import sqlalchemy as sa


revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "context_rules",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("conditions", sa.JSON(), nullable=False),
        sa.Column("persona_id", sa.String(36), nullable=False),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_context_rules_user_id", "context_rules", ["user_id"])

    # Add manual_override flag to user_context (SQLite-safe via batch)
    with op.batch_alter_table("user_context") as batch_op:
        batch_op.add_column(
            sa.Column(
                "manual_override",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("user_context") as batch_op:
        batch_op.drop_column("manual_override")

    op.drop_index("ix_context_rules_user_id", table_name="context_rules")
    op.drop_table("context_rules")
