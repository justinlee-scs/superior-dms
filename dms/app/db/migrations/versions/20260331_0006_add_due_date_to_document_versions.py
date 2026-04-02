"""add due_date to document_versions

Revision ID: 20260331_0006
Revises: 20260330_0005
Create Date: 2026-03-31 12:00:00
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260331_0006"
down_revision = "20260330_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("document_versions", sa.Column("due_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("document_versions", "due_date")
