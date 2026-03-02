from sqlalchemy import Table, Column, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


role_hierarchy = Table(
    "role_hierarchy",
    Base.metadata,
    Column("manager_role_id", UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False),
    Column("managed_role_id", UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False),
    UniqueConstraint("manager_role_id", "managed_role_id"),
    CheckConstraint("manager_role_id <> managed_role_id", name="ck_role_hierarchy_no_self"),
)
