"""Add source_model column to dashboard_specs and workflow_specs.

Tracks which Mental Model installed a dashboard or workflow so
model-sourced TBox surfaces can be cleaned up on uninstall.

Revision ID: 025
Revises: 024
Create Date: 2026-04-04
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "dashboard_specs",
        sa.Column("source_model", sa.String(64), nullable=True),
    )
    op.create_index(
        "ix_dashboard_specs_source_model",
        "dashboard_specs",
        ["source_model"],
    )

    op.add_column(
        "workflow_specs",
        sa.Column("source_model", sa.String(64), nullable=True),
    )
    op.create_index(
        "ix_workflow_specs_source_model",
        "workflow_specs",
        ["source_model"],
    )


def downgrade() -> None:
    op.drop_index("ix_workflow_specs_source_model", table_name="workflow_specs")
    op.drop_column("workflow_specs", "source_model")

    op.drop_index("ix_dashboard_specs_source_model", table_name="dashboard_specs")
    op.drop_column("dashboard_specs", "source_model")
