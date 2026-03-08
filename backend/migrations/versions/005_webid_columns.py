"""Add WebID profile columns to users table.

Revision ID: 005
Revises: 004
Create Date: 2026-03-08
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(63), nullable=True))
    op.add_column("users", sa.Column("public_key_pem", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("private_key_encrypted", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("webid_links", sa.Text(), nullable=True))
    op.add_column(
        "users",
        sa.Column("webid_published", sa.Boolean(), nullable=True, server_default=sa.false()),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_username", table_name="users")
    op.drop_column("users", "webid_published")
    op.drop_column("users", "webid_links")
    op.drop_column("users", "private_key_encrypted")
    op.drop_column("users", "public_key_pem")
    op.drop_column("users", "username")
