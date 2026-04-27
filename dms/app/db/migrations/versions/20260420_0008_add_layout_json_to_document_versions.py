"""add layout_json to document_versions

Revision ID: 20260420_0008
Revises: bb7e6a2c6d6e
Create Date: 2026-04-20 12:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "20260420_0008"
down_revision = "bb7e6a2c6d6e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("document_versions")}
    if "layout_json" not in columns:
        op.add_column(
            "document_versions",
            sa.Column("layout_json", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("document_versions")}
    if "layout_json" in columns:
        op.drop_column("document_versions", "layout_json")
