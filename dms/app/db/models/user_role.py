from sqlalchemy import Table, Column, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id"), nullable=False),
    Column("role_id", UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False),
    UniqueConstraint("user_id", "role_id"),
)
