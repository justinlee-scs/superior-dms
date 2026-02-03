from sqlalchemy import Table, Column, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False),
    Column("permission_id", UUID(as_uuid=True), ForeignKey("permissions.id"), nullable=False),
    UniqueConstraint("role_id", "permission_id"),
)
