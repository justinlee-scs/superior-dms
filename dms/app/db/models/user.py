from sqlalchemy import Column, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True)

    roles = relationship(
        "Role",
        secondary="user_roles",
        backref="users",
        lazy="selectin",
    )

    permission_overrides = relationship(
        "UserPermissionOverride",
        back_populates="user",
        lazy="selectin",
    )
