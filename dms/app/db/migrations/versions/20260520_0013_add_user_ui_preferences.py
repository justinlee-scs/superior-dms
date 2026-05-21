"""add user ui preferences

Revision ID: 20260520_0013
Revises: 20260506_0012
Create Date: 2026-05-20 15:30:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "20260520_0013"
down_revision = "20260506_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("users")}

    if "ui_dark_mode" not in columns:
        op.add_column(
            "users",
            sa.Column(
                "ui_dark_mode",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )
    if "ui_view_mode" not in columns:
        op.add_column(
            "users",
            sa.Column(
                "ui_view_mode",
                sa.String(length=32),
                nullable=False,
                server_default=sa.text("'compact'"),
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("users")}

    if "ui_view_mode" in columns:
        op.drop_column("users", "ui_view_mode")
    if "ui_dark_mode" in columns:
        op.drop_column("users", "ui_dark_mode")
