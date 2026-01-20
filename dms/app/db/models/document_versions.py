import uuid
from uuid import uuid4

import enum

import sqlalchemy as sa
from sqlalchemy import Column, ForeignKey, String, Text, Float
from sqlalchemy import Column, Enum as SQLEnum, DateTime
from datetime import datetime
from app.db.models.enums import DocumentClass
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class ProcessingStatus(enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id = Column(UUID(as_uuid=True), primary_key=True)

    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

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

    classification = Column(sa.String, nullable=True)
    confidence = Column(sa.Float, nullable=True)
    extracted_text = Column(sa.Text, nullable=True)
    
    # THIS relationship uses document_id
    document = relationship(
        "Document",
        back_populates="versions",
        foreign_keys=[document_id],
    )