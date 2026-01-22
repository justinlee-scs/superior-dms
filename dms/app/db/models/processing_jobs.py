from datetime import datetime
import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.db.models.enums import ProcessingStage, ProcessingStatus


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    document_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("document_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    stage = Column(
        Enum(ProcessingStage, name="processing_stage"),
        nullable=False,
    )

    status = Column(
        Enum(ProcessingStatus, name="processing_status"),
        nullable=False,
    )

    result = Column(
        JSONB,
        nullable=True,
        doc="Stage-specific output or error payload",
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    document_version = relationship(
        "DocumentVersion",
        back_populates="processing_jobs",
    )
