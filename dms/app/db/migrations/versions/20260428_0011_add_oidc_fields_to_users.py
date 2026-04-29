"""add oidc fields to users

Revision ID: 20260428_0011
Revises: 20260421_0010
Create Date: 2026-04-28 10:00:00
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260428_0011"
down_revision = "20260421_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("auth_provider", sa.String(), nullable=True))
    op.add_column("users", sa.Column("oidc_subject", sa.String(), nullable=True))
    op.execute("UPDATE users SET auth_provider = 'local' WHERE auth_provider IS NULL")
    op.alter_column("users", "auth_provider", nullable=False)
    op.create_index(op.f("ix_users_oidc_subject"), "users", ["oidc_subject"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_oidc_subject"), table_name="users")
    op.drop_column("users", "oidc_subject")
    op.drop_column("users", "auth_provider")
