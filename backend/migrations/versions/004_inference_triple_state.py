"""Add inference_triple_state table for per-triple dismiss/promote tracking.

Revision ID: 004
Revises: 003
Create Date: 2026-03-04
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inference_triple_state",
        sa.Column("triple_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("subject_iri", sa.Text(), nullable=False),
        sa.Column("predicate_iri", sa.Text(), nullable=False),
        sa.Column("object_iri", sa.Text(), nullable=False),
        sa.Column("entailment_type", sa.String(50), nullable=False),
        sa.Column("source_model_id", sa.String(100), nullable=True),
        sa.Column("inferred_at", sa.String(50), nullable=False),
        sa.Column("dismissed_at", sa.String(50), nullable=True),
        sa.Column("promoted_at", sa.String(50), nullable=True),
        sa.PrimaryKeyConstraint("triple_hash"),
    )


def downgrade() -> None:
    op.drop_table("inference_triple_state")
