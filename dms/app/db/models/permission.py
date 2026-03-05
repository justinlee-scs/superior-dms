from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.db.base import Base


class Permission(Base):
    """RBAC permission catalog entry that can be assigned to roles.

    Parameters:
        id: Primary identifier for this record.
        key: Unique permission key used in authorization checks.
        description: Optional human-readable description.
        created_at: Timestamp indicating when the record was created.
    """
    __tablename__ = "permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
