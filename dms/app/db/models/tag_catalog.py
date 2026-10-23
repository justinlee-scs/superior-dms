import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class TagCatalog(Base):
    """Represent the tag catalog database model.

    Parameters:
        id: Primary identifier for this record.
        name: Human-readable name for this entity.
        created_at: Timestamp indicating when the record was created.
    """
    __tablename__ = "tag_catalog"
    __table_args__ = (
        sa.CheckConstraint("kind IN ('label', 'document_type')", name="ck_tag_catalog_kind"),
        sa.UniqueConstraint("name", name="uq_tag_catalog_name"),
    )

    id = sa.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = sa.Column(sa.String(255), unique=True, nullable=False, index=True)
    kind = sa.Column(sa.String(32), nullable=False, default="label", server_default="label")
    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, default=datetime.utcnow)
