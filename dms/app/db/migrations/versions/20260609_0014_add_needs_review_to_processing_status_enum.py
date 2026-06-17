"""add needs review to processing_status_enum

Revision ID: 20260609_0014
Revises: 20260520_0013
Create Date: 2026-06-09 00:00:00
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260609_0014"
down_revision = "20260520_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ADD VALUE cannot run inside a transaction block in Postgres
    op.execute("COMMIT")
    op.execute("ALTER TYPE processing_status_enum ADD VALUE IF NOT EXISTS 'needs review'")


def downgrade() -> None:
    # Postgres does not support removing enum values natively.
    # To roll back, the enum type would need to be recreated without
    # 'needs review', which requires updating all dependent columns.
    # Left as a no-op — remove manually if needed.
    pass