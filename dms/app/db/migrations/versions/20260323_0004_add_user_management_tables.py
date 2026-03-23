"""add user management tables

Revision ID: 20260323_0004
Revises: 20260323_0003
Create Date: 2026-03-23 00:10:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260323_0004"
down_revision = "20260323_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_role_management",
        sa.Column("manager_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("managed_role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id"), nullable=False),
        sa.UniqueConstraint("manager_user_id", "managed_role_id"),
    )
    op.create_table(
        "user_user_management",
        sa.Column("manager_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("managed_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.UniqueConstraint("manager_user_id", "managed_user_id"),
        sa.CheckConstraint("manager_user_id <> managed_user_id", name="ck_user_user_management_no_self"),
    )


def downgrade() -> None:
    op.drop_table("user_user_management")
    op.drop_table("user_role_management")
