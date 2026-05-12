"""add oidc fields to users

Revision ID: 20260428_0011
Revises: 20260421_0010
Create Date: 2026-04-28 10:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "20260428_0011"
down_revision = "20260421_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("users")}

    if "auth_provider" not in columns:
        op.add_column("users", sa.Column("auth_provider", sa.String(), nullable=True))
    if "oidc_subject" not in columns:
        op.add_column("users", sa.Column("oidc_subject", sa.String(), nullable=True))

    op.execute("UPDATE users SET auth_provider = 'local' WHERE auth_provider IS NULL")
    op.alter_column("users", "auth_provider", nullable=False)
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_oidc_subject ON users (oidc_subject)"
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("users")}

    op.execute("DROP INDEX IF EXISTS ix_users_oidc_subject")
    if "oidc_subject" in columns:
        op.drop_column("users", "oidc_subject")
    if "auth_provider" in columns:
        op.drop_column("users", "auth_provider")
