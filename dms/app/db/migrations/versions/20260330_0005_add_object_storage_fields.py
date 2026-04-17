"""add object storage fields to document_versions

Revision ID: 20260330_0005
Revises: 20260323_0004
Create Date: 2026-03-30 12:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "20260330_0005"
down_revision = "20260323_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("document_versions")}

    if "storage_bucket" not in columns:
        op.add_column("document_versions", sa.Column("storage_bucket", sa.String(length=128), nullable=True))
    if "storage_key" not in columns:
        op.add_column("document_versions", sa.Column("storage_key", sa.String(length=512), nullable=True))
    if "storage_etag" not in columns:
        op.add_column("document_versions", sa.Column("storage_etag", sa.String(length=128), nullable=True))
    if "storage_size_bytes" not in columns:
        op.add_column("document_versions", sa.Column("storage_size_bytes", sa.Integer(), nullable=True))

    op.alter_column("document_versions", "content", nullable=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("document_versions")}

    op.alter_column("document_versions", "content", nullable=False)
    if "storage_size_bytes" in columns:
        op.drop_column("document_versions", "storage_size_bytes")
    if "storage_etag" in columns:
        op.drop_column("document_versions", "storage_etag")
    if "storage_key" in columns:
        op.drop_column("document_versions", "storage_key")
    if "storage_bucket" in columns:
        op.drop_column("document_versions", "storage_bucket")
