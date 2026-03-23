from sqlalchemy import Table, Column, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


user_user_management = Table(
    "user_user_management",
    Base.metadata,
    Column("manager_user_id", UUID(as_uuid=True), ForeignKey("users.id"), nullable=False),
    Column("managed_user_id", UUID(as_uuid=True), ForeignKey("users.id"), nullable=False),
    UniqueConstraint("manager_user_id", "managed_user_id"),
    CheckConstraint("manager_user_id <> managed_user_id", name="ck_user_user_management_no_self"),
)
