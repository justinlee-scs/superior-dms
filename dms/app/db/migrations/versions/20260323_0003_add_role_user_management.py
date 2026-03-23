"""add role user management table

Revision ID: 20260323_0003
Revises: 20260317_0002
Create Date: 2026-03-23 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260323_0003"
down_revision = "20260317_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "role_user_management",
        sa.Column("manager_role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("managed_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.UniqueConstraint("manager_role_id", "managed_user_id"),
    )


def downgrade() -> None:
    op.drop_table("role_user_management")
