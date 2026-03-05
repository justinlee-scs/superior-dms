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

    id = sa.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = sa.Column(sa.String(128), unique=True, nullable=False, index=True)
    created_at = sa.Column(sa.DateTime, nullable=False, default=datetime.utcnow)
