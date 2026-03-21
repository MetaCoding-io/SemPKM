"""Add lint filter tables: suppressions, dismissals, presets.

Revision ID: 015
Revises: 014
Create Date: 2026-03-20
"""

from alembic import op
import sqlalchemy as sa


revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Per-user rule suppressions (suppress entire rule type globally)
    op.create_table(
        "lint_suppressions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("rule_source_iri", sa.String(2048), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "user_id", "rule_source_iri", name="uq_lint_suppression"
        ),
    )

    # Per-user individual result dismissals (object + rule pair)
    op.create_table(
        "lint_dismissals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("object_iri", sa.String(2048), nullable=False),
        sa.Column("rule_source_iri", sa.String(2048), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "user_id",
            "object_iri",
            "rule_source_iri",
            name="uq_lint_dismissal",
        ),
    )

    # Named preset collections of suppressed rules
    op.create_table(
        "lint_presets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("suppressed_rules_json", sa.Text(), nullable=False, server_default="[]"),
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
        sa.UniqueConstraint("user_id", "name", name="uq_lint_preset"),
    )


def downgrade() -> None:
    op.drop_table("lint_presets")
    op.drop_table("lint_dismissals")
    op.drop_table("lint_suppressions")
