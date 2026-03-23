from sqlalchemy import Table, Column, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


user_role_management = Table(
    "user_role_management",
    Base.metadata,
    Column("manager_user_id", UUID(as_uuid=True), ForeignKey("users.id"), nullable=False),
    Column("managed_role_id", UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False),
    UniqueConstraint("manager_user_id", "managed_role_id"),
)
