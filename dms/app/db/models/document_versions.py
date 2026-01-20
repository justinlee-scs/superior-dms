from uuid import uuid4

from sqlalchemy import Column, ForeignKey, String, Text, Float
from sqlalchemy import Column, Enum as SQLEnum, DateTime
from datetime import datetime
from app.db.models.enums import DocumentClass
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    filename = Column(String, nullable=False)
    processing_status = Column(String, nullable=False)  # uploaded | processing | complete | failed
    classification = Column(
    SQLEnum(DocumentClass, name="document_class"),
    nullable=False,
    default=DocumentClass.UNKNOWN,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    extracted_text = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)

    document = relationship("Document", back_populates="versions")
