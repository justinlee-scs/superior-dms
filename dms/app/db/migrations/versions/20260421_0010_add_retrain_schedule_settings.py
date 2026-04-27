"""add retrain schedule settings table

Revision ID: 20260421_0010
Revises: 20260421_0009
Create Date: 2026-04-21 10:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260421_0010"
down_revision = "20260421_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "retrain_schedule_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="America/Los_Angeles"),
        sa.Column("hour", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("minute", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        """
        INSERT INTO retrain_schedule_settings (id, enabled, timezone, hour, minute, updated_at)
        VALUES (1, true, 'America/Los_Angeles', 3, 0, NOW())
        ON CONFLICT (id) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.drop_table("retrain_schedule_settings")
