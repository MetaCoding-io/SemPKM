"""Create user_favorites table.

Revision ID: 009
Revises: 008
Create Date: 2026-03-12
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_favorites",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("object_iri", sa.String(2048), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "object_iri", name="uq_user_favorite"),
    )
    op.create_index("ix_user_favorites_user_id", "user_favorites", ["user_id"])


def downgrade() -> None:
    op.drop_table("user_favorites")
