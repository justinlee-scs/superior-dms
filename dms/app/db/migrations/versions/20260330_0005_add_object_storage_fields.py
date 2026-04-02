"""add object storage fields to document_versions

Revision ID: 20260330_0005
Revises: 20260323_0004
Create Date: 2026-03-30 12:00:00
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260330_0005"
down_revision = "20260323_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("document_versions", sa.Column("storage_bucket", sa.String(length=128), nullable=True))
    op.add_column("document_versions", sa.Column("storage_key", sa.String(length=512), nullable=True))
    op.add_column("document_versions", sa.Column("storage_etag", sa.String(length=128), nullable=True))
    op.add_column("document_versions", sa.Column("storage_size_bytes", sa.Integer(), nullable=True))
    op.alter_column("document_versions", "content", nullable=True)


def downgrade() -> None:
    op.alter_column("document_versions", "content", nullable=False)
    op.drop_column("document_versions", "storage_size_bytes")
    op.drop_column("document_versions", "storage_etag")
    op.drop_column("document_versions", "storage_key")
    op.drop_column("document_versions", "storage_bucket")
