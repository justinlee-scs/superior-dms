from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class TrainingFeedbackEvent(Base):
    __tablename__ = "training_feedback_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("document_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    edited_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    source = Column(sa.String(32), nullable=False, default="dms_ui")
    event_type = Column(sa.String(64), nullable=False)

    predicted_tags = Column(sa.JSON, nullable=True)
    final_tags = Column(sa.JSON, nullable=True)
    predicted_document_type = Column(sa.String(64), nullable=True)
    final_document_type = Column(sa.String(64), nullable=True)

    extracted_text_snapshot = Column(sa.Text, nullable=True)
    model_confidence = Column(sa.Float, nullable=True)
    model_version = Column(sa.String(128), nullable=True)

    include_in_training = Column(sa.Boolean, nullable=False, default=True)
    created_at = Column(sa.DateTime, nullable=False, default=datetime.utcnow, index=True)
