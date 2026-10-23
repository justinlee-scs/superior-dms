import enum
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, object_session
from datetime import datetime

from app.db.base import Base


class DocumentType(enum.Enum):
    """Business document-type taxonomy persisted on `Document` records.

    Parameters:
        document: Document value used by this model/schema.
        invoice: Invoice value used by this model/schema.
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
    invoice = "invoice"
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
    created_at = Column(sa.DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    uploaded_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    document_type_tag_id = Column(UUID(as_uuid=True), ForeignKey("tag_catalog.id", ondelete="SET NULL", name="fk_documents_document_type_tag_id"), nullable=True)
    data = Column(JSONB, nullable=False, default=dict, server_default=sa.text("'{}'::jsonb"))
    due_date = Column(sa.Date, nullable=True)
    workflow_notes = Column(sa.Text, nullable=True)

    document_type_tag = relationship("TagCatalog", foreign_keys=[document_type_tag_id])
    tags = relationship("TagCatalog", secondary="document_tags", lazy="selectin")

    @property
    def document_type(self):
        return self.document_type_tag.name if self.document_type_tag else None

    @property
    def label_tags(self):
        return [
            tag.name for tag in (self.tags or [])
            if tag.kind == "label"
            and not tag.name.startswith(("due_date:", "payment_due_date:"))
        ]

    @label_tags.setter
    def label_tags(self, names):
        from app.db.models.tag_catalog import TagCatalog
        db = object_session(self)
        desired = set(names or [])
        keep = [
            tag for tag in (self.tags or [])
            if tag.kind != "label"
            and not tag.name.startswith(("due_date:", "payment_due_date:"))
        ]
        for name in sorted(desired):
            row = db.query(TagCatalog).filter_by(name=name).one_or_none() if db else None
            if row is None and db:
                row = TagCatalog(name=name, kind="label")
                db.add(row)
                db.flush()
            if row and row.kind == "label":
                keep.append(row)
        self.tags = keep

    @document_type.setter
    def document_type(self, name):
        if name is None:
            self.document_type_tag = None
            return
        from app.db.models.tag_catalog import TagCatalog
        db = object_session(self)
        if db is None:
            raise ValueError("Document must be attached to a session to set its type")
        name = str(getattr(name, "value", name)).lower()
        tag = db.query(TagCatalog).filter_by(name=name, kind="document_type").one_or_none()
        if tag is None:
            tag = TagCatalog(name=name, kind="document_type")
            db.add(tag)
            db.flush()
        self.document_type_tag = tag


    # POINTS TO THE ACTIVE VERSION
    current_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("document_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    in_workspace = Column(sa.Boolean, nullable=False, default=False, server_default="false")

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

    uploaded_by_user = relationship(
        "User",
        foreign_keys=[uploaded_by_user_id],
        lazy="selectin",
    )


# Association table added by migration 20260925_0019.
document_tags = Table(
    "document_tags",
    Base.metadata,
    Column("document_id", UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", UUID(as_uuid=True), ForeignKey("tag_catalog.id", ondelete="CASCADE"), primary_key=True, index=True),
    Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
)
