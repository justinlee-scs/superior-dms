from sqlalchemy import Table, Column, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


role_user_management = Table(
    "role_user_management",
    Base.metadata,
    Column("manager_role_id", UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False),
    Column("managed_user_id", UUID(as_uuid=True), ForeignKey("users.id"), nullable=False),
    UniqueConstraint("manager_role_id", "managed_user_id"),
)
