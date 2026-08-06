"""add_in_workspace_to_documents

Revision ID: 3563ac10025d
Revises: 20260623_0016
Create Date: 2026-07-15 15:59:22.159577
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20260715_0017'
down_revision = '20260623_0016'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('documents', sa.Column('in_workspace', sa.Boolean(), server_default='false', nullable=False))


def downgrade() -> None:
    op.drop_column('documents', 'in_workspace')