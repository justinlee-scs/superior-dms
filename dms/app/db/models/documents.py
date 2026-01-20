import enum
import sqlalchemy as sa
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime 

from app.db.base import Base

class DocumentType(enum.Enum):
    document = "document"
    statement = "statement"
    outgoing_invoice = "outgoing_invoice"
    incoming_invoice = "incoming_invoice"
    contract = "contract"
    payroll = "payroll"
    manual = "manual"
    receipt = "receipt"
    other = "other"


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True)
    filename = Column(sa.String, nullable=False)
    created_at = Column(sa.DateTime, nullable=False, default=datetime.utcnow)

    document_type = Column(
        sa.Enum(
            DocumentType,
            name="document_type_enum",
            native_enum=True,
            validate_strings=True,
        ),
        nullable=True
    )
    
    versions = relationship(
        "DocumentVersion",
        back_populates="document",
        cascade="all, delete-orphan",
    )

    content_hash = Column(sa.String(64), index=True)
