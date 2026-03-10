"""Create shared_query_access and promoted_query_views tables.

Revision ID: 008
Revises: 007
Create Date: 2026-03-10
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shared_query_access",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "query_id",
            sa.Uuid(),
            sa.ForeignKey("saved_sparql_queries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "shared_with_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("shared_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("query_id", "shared_with_user_id", name="uq_shared_query_user"),
    )
    op.create_index("ix_shared_query_access_query_id", "shared_query_access", ["query_id"])
    op.create_index(
        "ix_shared_query_access_shared_with_user_id",
        "shared_query_access",
        ["shared_with_user_id"],
    )

    op.create_table(
        "promoted_query_views",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "query_id",
            sa.Uuid(),
            sa.ForeignKey("saved_sparql_queries.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("display_label", sa.String(255), nullable=False),
        sa.Column("renderer_type", sa.String(20), server_default="table"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_promoted_query_views_user_id", "promoted_query_views", ["user_id"])


def downgrade() -> None:
    op.drop_table("promoted_query_views")
    op.drop_table("shared_query_access")
