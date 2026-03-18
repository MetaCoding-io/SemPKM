"""Add app platform tables for instance lifecycle, task runs, config, renderers, permissions.

Revision ID: 014
Revises: 013
Create Date: 2026-03-18
"""

from alembic import op
import sqlalchemy as sa


revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # App instance registry — one row per installed app
    op.create_table(
        "app_instances",
        sa.Column("app_id", sa.Text(), primary_key=True),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="stopped"),
        sa.Column("pid", sa.Integer(), nullable=True),
        sa.Column("socket_path", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "installed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("manifest_hash", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("restart_count", sa.Integer(), nullable=False, server_default="0"),
    )

    # Task execution history
    op.create_table(
        "app_task_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "app_id",
            sa.Text(),
            sa.ForeignKey("app_instances.app_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("task_id", sa.Text(), nullable=False),
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="running"),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_app_task_runs_app_id_task_id", "app_task_runs", ["app_id", "task_id"]
    )

    # Task interval overrides (user-adjusted)
    op.create_table(
        "app_task_config",
        sa.Column(
            "app_id",
            sa.Text(),
            sa.ForeignKey("app_instances.app_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("task_id", sa.Text(), primary_key=True),
        sa.Column("interval_override", sa.Text(), nullable=True),
        sa.Column("paused", sa.Boolean(), nullable=False, server_default="0"),
    )

    # Renderer preference overrides
    op.create_table(
        "app_renderer_prefs",
        sa.Column("type_iri", sa.Text(), primary_key=True),
        sa.Column("mode", sa.Text(), primary_key=True),
        sa.Column(
            "app_id",
            sa.Text(),
            sa.ForeignKey("app_instances.app_id", ondelete="CASCADE"),
            nullable=False,
        ),
    )

    # Approved permissions snapshot
    op.create_table(
        "app_permissions",
        sa.Column(
            "app_id",
            sa.Text(),
            sa.ForeignKey("app_instances.app_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("permissions_json", sa.Text(), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_by", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    # Drop in reverse dependency order (children before parent)
    op.drop_table("app_permissions")
    op.drop_table("app_renderer_prefs")
    op.drop_table("app_task_config")
    op.drop_index("ix_app_task_runs_app_id_task_id", table_name="app_task_runs")
    op.drop_table("app_task_runs")
    op.drop_table("app_instances")
