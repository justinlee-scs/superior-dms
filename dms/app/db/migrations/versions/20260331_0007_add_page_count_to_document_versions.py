"""add page_count to document_versions

Revision ID: 20260331_0007
Revises: 20260331_0006
Create Date: 2026-03-31 13:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "20260331_0007"
down_revision = "20260331_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("document_versions")}
    if "page_count" not in columns:
        op.add_column("document_versions", sa.Column("page_count", sa.Integer(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("document_versions")}
    if "page_count" in columns:
        op.drop_column("document_versions", "page_count")
