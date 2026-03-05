import enum
import sqlalchemy as sa
from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class DocumentType(enum.Enum):
    """Business document-type taxonomy persisted on `Document` records.

    Parameters:
        document: Document value used by this model/schema.
        statement: Statement value used by this model/schema.
        outgoing_invoice: Outgoing invoice value used by this model/schema.
        incoming_invoice: Incoming invoice value used by this model/schema.
        contract: Contract value used by this model/schema.
        payroll: Payroll value used by this model/schema.
        manual: Manual value used by this model/schema.
        receipt: Receipt value used by this model/schema.
        other: Other value used by this model/schema.
    """
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
    """Top-level document entity that owns versions and the active version pointer.

    Parameters:
        id: Primary identifier for this record.
        filename: Original filename for the uploaded document.
        created_at: Timestamp indicating when the record was created.
        content_hash: Deterministic hash used for duplicate-content detection.
        document_type: Document type/category assigned to the record.
        current_version_id: Identifier of the currently active version.
        versions: Versions value used by this model/schema.
        current_version: Current version value used by this model/schema.
    """
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True)
    filename = Column(sa.String, nullable=False)
    created_at = Column(sa.DateTime, nullable=False, default=datetime.utcnow)

    content_hash = Column(sa.String(64), index=True, nullable=False)

    document_type = Column(
        sa.Enum(
            DocumentType,
            name="document_type_enum",
            native_enum=True,
            validate_strings=True,
        ),
        nullable=True,
    )

    # POINTS TO THE ACTIVE VERSION
    current_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("document_versions.id", ondelete="SET NULL"),
        nullable=True,
    )

    versions = relationship(
        "DocumentVersion",
        back_populates="document",
        foreign_keys="DocumentVersion.document_id",
        cascade="all, delete-orphan",
    )
    
    # ACTIVE version (no backref)
    current_version = relationship(
        "DocumentVersion",
        foreign_keys=[current_version_id],
        post_update=True,
    )
