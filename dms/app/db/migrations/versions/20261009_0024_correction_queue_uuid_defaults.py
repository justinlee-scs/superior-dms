"""Give correction queue rows database-generated UUID primary keys.

Revision ID: 20261009_0024
Revises: 20260925_0023
Create Date: 2026-10-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261009_0024"
down_revision = "20260925_0023"
branch_labels = None
depends_on = None


def upgrade():
    for table in (
        "ocr_correction_queue",
        "ocr_word_boxes",
        "extraction_field_corrections",
    ):
        op.alter_column(
            table,
            "id",
            existing_type=postgresql.UUID(as_uuid=True),
            existing_nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        )


def downgrade():
    for table in (
        "extraction_field_corrections",
        "ocr_word_boxes",
        "ocr_correction_queue",
    ):
        op.alter_column(
            table,
            "id",
            existing_type=postgresql.UUID(as_uuid=True),
            existing_nullable=False,
            server_default=None,
        )
