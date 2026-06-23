"""add full_name to users

Revision ID: 20260619_0015
Revises: 20260609_0014
Create Date: 2026-06-19
"""
from alembic import op
import sqlalchemy as sa

revision = "20260619_0015"
down_revision = "20260609_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR")


def downgrade() -> None:
    op.drop_column("users", "full_name")