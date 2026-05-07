import sqlalchemy as sa
from sqlalchemy import Column, ForeignKey, Text, Float, LargeBinary
from datetime import datetime
from app.db.models.enums import DocumentClass, ProcessingStatus
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class DocumentVersion(Base):
    """Represent the document version database model.

    Parameters:
        id: Primary identifier for this record.
        document_id: Identifier of the parent document.
        content: Binary file content for the stored document version.
        extracted_text: Extracted plain text generated from OCR/parsing.
        classification: Predicted document class label.
        confidence: Model confidence score for the classification/output.
        ocr_raw_confidence: Raw OCR confidence score from the extraction engine.
        ocr_engine: Name of the OCR engine used for extraction.
        ocr_model_version: Version string of the OCR model used.
        ocr_latency_ms: OCR processing latency in milliseconds.
        tags: Normalized tags associated with the document/version.
        created_at: Timestamp indicating when the record was created.
        processing_status: Current processing state for this document version.
        document: Document value used by this model/schema.
    """

    __tablename__ = "document_versions"

    __table_args__ = (
        sa.UniqueConstraint("document_id", "version_number", name="uq_doc_version"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True)

    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number = Column(sa.Integer, nullable=False)
    content = Column(LargeBinary, nullable=True)

    storage_bucket = Column(sa.String(128), nullable=True)
    storage_key = Column(sa.String(512), nullable=True)
    storage_etag = Column(sa.String(128), nullable=True)
    storage_size_bytes = Column(sa.Integer, nullable=True)

    extracted_text = Column(Text, nullable=True)

    due_date = Column(sa.Date, nullable=True)

    classification = Column(
        sa.Enum(
            DocumentClass,
            name="document_class_enum",
            native_enum=True,
        ),
        nullable=True,
    )

    confidence = Column(Float, nullable=True)
    ocr_raw_confidence = Column(Float, nullable=True)
    ocr_engine = Column(sa.String(64), nullable=True)
    ocr_model_version = Column(sa.String(128), nullable=True)
    ocr_latency_ms = Column(sa.Integer, nullable=True)

    tags = Column(sa.JSON, nullable=False, default=list)

    page_count = Column(sa.Integer, nullable=True)

    created_at = Column(sa.DateTime, nullable=False, default=datetime.utcnow)

    processing_status = Column(
        sa.Enum(
            ProcessingStatus,
            name="processing_status_enum",
            native_enum=True,
        ),
        nullable=False,
        default=ProcessingStatus.pending,
    )

    layout_json = Column(sa.JSON, nullable=True)
    workflow_notes = Column(sa.Text, nullable=True)

    # THIS relationship uses document_id
    document = relationship(
        "Document",
        back_populates="versions",
        foreign_keys=[document_id],
    )
