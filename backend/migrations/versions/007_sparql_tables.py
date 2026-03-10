"""Create SPARQL query history and saved queries tables.

Revision ID: 007
Revises: 006
Create Date: 2026-03-10
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sparql_query_history",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_sparql_query_history_user_id", "sparql_query_history", ["user_id"])

    op.create_table(
        "saved_sparql_queries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_saved_sparql_queries_user_id", "saved_sparql_queries", ["user_id"])


def downgrade() -> None:
    op.drop_table("saved_sparql_queries")
    op.drop_table("sparql_query_history")
