"""Drop query-related SQL tables (migrated to RDF triplestore).

Tables dropped:
- promoted_query_views (-> urn:sempkm:vocab:PromotedView in RDF)
- shared_query_access  (-> sempkm:sharedWith predicates in RDF)
- saved_sparql_queries  (-> urn:sempkm:vocab:SavedQuery in RDF)
- sparql_query_history  (-> urn:sempkm:vocab:QueryExecution in RDF)

Run POST /admin/migrate-queries before applying this migration
to ensure data is preserved in the triplestore.

Revision ID: 010
Revises: 009
Create Date: 2026-03-14
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop in FK dependency order
    op.drop_table("promoted_query_views")
    op.drop_table("shared_query_access")
    op.drop_table("saved_sparql_queries")
    op.drop_table("sparql_query_history")


def downgrade() -> None:
    # Recreate tables (from migrations 007 and 008)
    op.create_table(
        "sparql_query_history",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_sparql_query_history_user_id", "sparql_query_history", ["user_id"])

    op.create_table(
        "saved_sparql_queries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_saved_sparql_queries_user_id", "saved_sparql_queries", ["user_id"])

    op.create_table(
        "shared_query_access",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "query_id", sa.Uuid(),
            sa.ForeignKey("saved_sparql_queries.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "shared_with_user_id", sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("shared_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("query_id", "shared_with_user_id", name="uq_shared_query_user"),
    )
    op.create_index("ix_shared_query_access_query_id", "shared_query_access", ["query_id"])
    op.create_index(
        "ix_shared_query_access_shared_with_user_id",
        "shared_query_access", ["shared_with_user_id"],
    )

    op.create_table(
        "promoted_query_views",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "query_id", sa.Uuid(),
            sa.ForeignKey("saved_sparql_queries.id", ondelete="CASCADE"),
            nullable=False, unique=True,
        ),
        sa.Column(
            "user_id", sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("display_label", sa.String(255), nullable=False),
        sa.Column("renderer_type", sa.String(20), server_default="table"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_promoted_query_views_user_id", "promoted_query_views", ["user_id"])
