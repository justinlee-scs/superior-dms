import uuid
from sqlalchemy import Column, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)

    roles = relationship(
        "Role",
        secondary="user_roles",
        back_populates="users",
        lazy="selectin",
    )

    permission_overrides = relationship(
        "UserPermissionOverride",
        back_populates="user",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    def has_role(self, role_name: str) -> bool:
        return any(role.name == role_name for role in self.roles)

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
