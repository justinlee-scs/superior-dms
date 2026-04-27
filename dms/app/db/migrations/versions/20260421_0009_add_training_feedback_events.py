"""add training feedback events table

Revision ID: 20260421_0009
Revises: 20260420_0008
Create Date: 2026-04-21 03:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260421_0009"
down_revision = "20260420_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "training_feedback_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("document_version_id", sa.UUID(), nullable=True),
        sa.Column("edited_by_user_id", sa.UUID(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("predicted_tags", sa.JSON(), nullable=True),
        sa.Column("final_tags", sa.JSON(), nullable=True),
        sa.Column("predicted_document_type", sa.String(length=64), nullable=True),
        sa.Column("final_document_type", sa.String(length=64), nullable=True),
        sa.Column("extracted_text_snapshot", sa.Text(), nullable=True),
        sa.Column("model_confidence", sa.Float(), nullable=True),
        sa.Column("model_version", sa.String(length=128), nullable=True),
        sa.Column(
            "include_in_training",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["document_version_id"], ["document_versions.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["edited_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_training_feedback_events_document_id"),
        "training_feedback_events",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_training_feedback_events_document_version_id"),
        "training_feedback_events",
        ["document_version_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_training_feedback_events_edited_by_user_id"),
        "training_feedback_events",
        ["edited_by_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_training_feedback_events_created_at"),
        "training_feedback_events",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_training_feedback_events_created_at"), table_name="training_feedback_events")
    op.drop_index(op.f("ix_training_feedback_events_edited_by_user_id"), table_name="training_feedback_events")
    op.drop_index(op.f("ix_training_feedback_events_document_version_id"), table_name="training_feedback_events")
    op.drop_index(op.f("ix_training_feedback_events_document_id"), table_name="training_feedback_events")
    op.drop_table("training_feedback_events")
