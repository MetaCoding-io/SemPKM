"""Add security_audit_log table (F-029).

Revision ID: 024
Revises: 023
Create Date: 2026-03-25
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "security_audit_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("source_ip", sa.String(45), nullable=False),
        sa.Column("detail", sa.Text(), server_default="{}", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_security_audit_log_event_type", "security_audit_log", ["event_type"])
    op.create_index("ix_security_audit_log_user_id", "security_audit_log", ["user_id"])
    op.create_index("ix_security_audit_log_created_at", "security_audit_log", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_security_audit_log_created_at", table_name="security_audit_log")
    op.drop_index("ix_security_audit_log_user_id", table_name="security_audit_log")
    op.drop_index("ix_security_audit_log_event_type", table_name="security_audit_log")
    op.drop_table("security_audit_log")
