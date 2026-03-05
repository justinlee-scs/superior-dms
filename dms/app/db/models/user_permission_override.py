from sqlalchemy import Column, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
import uuid

from app.db.base import Base


class PermissionEffect(enum.Enum):
    """Define the permission effect enumeration values.

    Parameters:
        ALLOW: Enumeration member representing an allowed constant value.
        DENY: Enumeration member representing an allowed constant value.
    """
    ALLOW = "ALLOW"
    DENY = "DENY"


class UserPermissionOverride(Base):
    """Represent the user permission override database model.

    Parameters:
        id: Primary identifier for this record.
        user_id: Identifier of the user this record belongs to.
        permission_id: Identifier of the referenced permission.
        effect: Override effect determining whether access is allowed or denied.
        user: User value used by this model/schema.
        permission: Permission value used by this model/schema.
    """
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
