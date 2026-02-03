from sqlalchemy import Column, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
import uuid

from app.db.base import Base


class PermissionEffect(enum.Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"


class UserPermissionOverride(Base):
    __tablename__ = "user_permission_overrides"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    permission_id = Column(UUID(as_uuid=True), ForeignKey("permissions.id"), nullable=False)
    effect = Column(Enum(PermissionEffect), nullable=False)

    user = relationship("User", back_populates="permission_overrides")
    permission = relationship("Permission")

    __table_args__ = (
        UniqueConstraint("user_id", "permission_id"),
    )
