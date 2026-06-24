"""add created_by_user_id to document_versions

Revision ID: 20260623_0016
Revises: 20260619_0015
Create Date: 2026-06-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260623_0016"
down_revision = "20260619_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("document_versions")}

    if "created_by_user_id" not in columns:
        op.add_column(
            "document_versions",
            sa.Column("created_by_user_id", sa.UUID(), nullable=True),
        )
        op.create_index(
            "ix_document_versions_created_by_user_id",
            "document_versions",
            ["created_by_user_id"],
        )
        op.create_foreign_key(
            "fk_document_versions_created_by_user_id_users",
            "document_versions",
            "users",
            ["created_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("document_versions")}

    if "created_by_user_id" in columns:
        op.drop_constraint(
            "fk_document_versions_created_by_user_id_users",
            "document_versions",
            type_="foreignkey",
        )
        op.drop_index(
            "ix_document_versions_created_by_user_id",
            table_name="document_versions",
        )
        op.drop_column("document_versions", "created_by_user_id")
