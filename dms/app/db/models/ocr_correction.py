"""
app/db/models/ocr_correction.py

ORM models for the three tables added by migration
20260826_0018_add_doctr_correction_queue.py. Matches the Column(...)
declarative style used in document_versions.py / documents.py (not the
newer Mapped[...]/mapped_column typed style) for consistency with the
rest of app/db/models/.
"""
import enum
import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import Column, ForeignKey, Text, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.session import Base  # matches document_versions.py's actual import


class CorrectionStatus(str, enum.Enum):
    pending = "pending"
    in_review = "in_review"
    confirmed = "confirmed"


class OCRCorrectionQueue(Base):
    """One row per document version flagged for field-value correction."""

    __tablename__ = "ocr_correction_queue"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=sa.text("gen_random_uuid()"))
    document_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("document_versions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    status = Column(
        sa.Enum(CorrectionStatus, name="correction_status_enum", native_enum=True),
        nullable=False,
        default=CorrectionStatus.pending,
    )
    created_at = Column(sa.DateTime, nullable=False, default=datetime.utcnow)
    confirmed_at = Column(sa.DateTime, nullable=True)
    confirmed_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    document_version = relationship("DocumentVersion", backref="correction_queue_item")


class OCRWordBox(Base):
    """Per-word OCR output - background data only. Not directly edited by
    the correction UI (which is field-level only); kept to explain *why*
    a document was flagged and for future detection/recognition
    fine-tuning."""

    __tablename__ = "ocr_word_boxes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=sa.text("gen_random_uuid()"))
    document_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("document_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page = Column(sa.Integer, nullable=False)
    bbox = Column(JSONB, nullable=False)  # [x0, y0, x1, y1] normalized 0-1
    text_raw = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False, index=True)

    document_version = relationship("DocumentVersion", backref="ocr_word_boxes")


class ExtractionFieldCorrection(Base):
    """A single field-value correction - what the correction UI actually
    writes when a user edits an extracted field."""

    __tablename__ = "extraction_field_corrections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=sa.text("gen_random_uuid()"))
    document_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("document_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field_name = Column(sa.String(64), nullable=False)
    value_raw = Column(Text, nullable=True)
    value_corrected = Column(Text, nullable=True)
    created_at = Column(sa.DateTime, nullable=False, default=datetime.utcnow)

    document_version = relationship("DocumentVersion", backref="field_corrections")