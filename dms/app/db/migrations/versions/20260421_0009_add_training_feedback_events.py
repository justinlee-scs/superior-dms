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
    op.execute("""
    DO $$ BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'training_feedback_events') THEN
            CREATE TABLE training_feedback_events (
                id UUID NOT NULL,
                document_id UUID NOT NULL,
                document_version_id UUID,
                edited_by_user_id UUID,
                source VARCHAR(32) NOT NULL,
                event_type VARCHAR(64) NOT NULL,
                predicted_tags JSON,
                final_tags JSON,
                predicted_document_type VARCHAR(64),
                final_document_type VARCHAR(64),
                extracted_text_snapshot TEXT,
                model_confidence FLOAT,
                model_version VARCHAR(128),
                include_in_training BOOLEAN DEFAULT true NOT NULL,
                created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                PRIMARY KEY (id),
                FOREIGN KEY(document_id) REFERENCES documents (id) ON DELETE CASCADE,
                FOREIGN KEY(document_version_id) REFERENCES document_versions (id) ON DELETE SET NULL,
                FOREIGN KEY(edited_by_user_id) REFERENCES users (id) ON DELETE SET NULL
            );
        END IF;
    END $$;
        """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_training_feedback_events_document_id ON training_feedback_events (document_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_training_feedback_events_document_version_id ON training_feedback_events (document_version_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_training_feedback_events_edited_by_user_id ON training_feedback_events (edited_by_user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_training_feedback_events_created_at ON training_feedback_events (created_at)"
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_training_feedback_events_created_at"),
        table_name="training_feedback_events",
    )
    op.drop_index(
        op.f("ix_training_feedback_events_edited_by_user_id"),
        table_name="training_feedback_events",
    )
    op.drop_index(
        op.f("ix_training_feedback_events_document_version_id"),
        table_name="training_feedback_events",
    )
    op.drop_index(
        op.f("ix_training_feedback_events_document_id"),
        table_name="training_feedback_events",
    )
    op.drop_table("training_feedback_events")
