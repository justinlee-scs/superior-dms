from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class WorkspaceDocument(Base):
    """Per-user private workspace marker for documents."""

    __tablename__ = "workspace_documents"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    created_at = Column(sa.DateTime, nullable=False, default=datetime.utcnow)
