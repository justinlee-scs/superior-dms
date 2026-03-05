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

    id = Column(UUID(as_uuid=True), primary_key=True)

    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    content = Column(LargeBinary, nullable=False)
    
    extracted_text = Column(Text, nullable=True)

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
    
    # THIS relationship uses document_id
    document = relationship(
        "Document",
        back_populates="versions",
        foreign_keys=[document_id],
    )
