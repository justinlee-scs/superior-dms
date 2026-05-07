"""add workflow notes and needs review status

Revision ID: 20260506_0012
Revises: 20260428_0011
Create Date: 2026-05-06
"""

from alembic import op
import sqlalchemy as sa


revision = "20260506_0012"
down_revision = "20260428_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE processing_status_enum ADD VALUE IF NOT EXISTS 'needs review'")
    op.add_column("document_versions", sa.Column("workflow_notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("document_versions", "workflow_notes")
