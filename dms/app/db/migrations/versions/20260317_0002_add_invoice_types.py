"""add incoming/outgoing invoice enums

Revision ID: 20260317_0002
Revises: 20260306_0001
Create Date: 2026-03-17 12:00:00
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "20260317_0002"
down_revision = "20260306_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE document_class_enum ADD VALUE IF NOT EXISTS 'incoming_invoice'")
    op.execute("ALTER TYPE document_class_enum ADD VALUE IF NOT EXISTS 'outgoing_invoice'")
    op.execute("ALTER TYPE document_type_enum ADD VALUE IF NOT EXISTS 'invoice'")


def downgrade() -> None:
    # Enum value removal is not supported without a more invasive migration.
    pass
