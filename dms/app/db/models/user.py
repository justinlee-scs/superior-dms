import uuid
from sqlalchemy import Column, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class User(Base):
    """Represent the user database model.

    Parameters:
        id: Primary identifier for this record.
        email: User email address used for login and contact.
        username: Unique username used to identify the user.
        hashed_password: Stored password hash for authentication checks.
        is_active: Whether the user account or entity is active.
        roles: Roles assigned to the user.
        permission_overrides: Per-user permission overrides that allow or deny specific actions.
        managed_by_roles: Roles that are allowed to manage this user.
        managed_roles: Roles that this user is allowed to manage.
        managed_users: Users that this user is allowed to manage.
        managed_by_users: Users that are allowed to manage this user.
    """
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

    managed_by_roles = relationship(
        "Role",
        secondary="role_user_management",
        primaryjoin="User.id == role_user_management.c.managed_user_id",
        secondaryjoin="Role.id == role_user_management.c.manager_role_id",
        lazy="selectin",
    )

    managed_roles = relationship(
        "Role",
        secondary="user_role_management",
        primaryjoin="User.id == user_role_management.c.manager_user_id",
        secondaryjoin="Role.id == user_role_management.c.managed_role_id",
        lazy="selectin",
    )

    managed_users = relationship(
        "User",
        secondary="user_user_management",
        primaryjoin="User.id == user_user_management.c.manager_user_id",
        secondaryjoin="User.id == user_user_management.c.managed_user_id",
        lazy="selectin",
    )

    managed_by_users = relationship(
        "User",
        secondary="user_user_management",
        primaryjoin="User.id == user_user_management.c.managed_user_id",
        secondaryjoin="User.id == user_user_management.c.manager_user_id",
        lazy="selectin",
    )

    def has_role(self, role_name: str) -> bool:
        """Handle has role for this instance.

        Parameters:
            role_name (type=str): Role name to check against the user's assigned roles.
        """
        return any(role.name == role_name for role in self.roles)

    def __repr__(self) -> str:
        """Return a debug-friendly string representation of the instance.

        Parameters:
            None.
        """
        return f"<User id={self.id} email={self.email}>"
