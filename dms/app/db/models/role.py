from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.db.base import Base
from app.db.models.role_hierarchy import role_hierarchy
from app.db.models.role_user_management import role_user_management
from app.db.models.user_role_management import user_role_management


class Role(Base):
    """Represent the role database model.

    Parameters:
        id: Primary identifier for this record.
        name: Human-readable name for this entity.
        description: Optional human-readable description.
        users: Users value used by this model/schema.
        permissions: Permissions associated with the role or response.
        managed_roles: Roles that this role is allowed to manage.
        manager_roles: Roles that are allowed to manage this role.
        managed_users: Users that this role is allowed to manage.
        manager_users: Users that are allowed to manage this role.
    """
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)

    users = relationship(
        "User",
        secondary="user_roles",
        back_populates="roles",
        lazy="selectin",
    )

    permissions = relationship(
        "Permission",
        secondary="role_permissions",
        backref="roles",
        lazy="selectin",
    )

    managed_roles = relationship(
        "Role",
        secondary=role_hierarchy,
        primaryjoin=id == role_hierarchy.c.manager_role_id,
        secondaryjoin=id == role_hierarchy.c.managed_role_id,
        lazy="selectin",
    )

    manager_roles = relationship(
        "Role",
        secondary=role_hierarchy,
        primaryjoin=id == role_hierarchy.c.managed_role_id,
        secondaryjoin=id == role_hierarchy.c.manager_role_id,
        lazy="selectin",
    )

    managed_users = relationship(
        "User",
        secondary=role_user_management,
        primaryjoin=id == role_user_management.c.manager_role_id,
        secondaryjoin="User.id == role_user_management.c.managed_user_id",
        lazy="selectin",
    )

    manager_users = relationship(
        "User",
        secondary=user_role_management,
        primaryjoin=id == user_role_management.c.managed_role_id,
        secondaryjoin="User.id == user_role_management.c.manager_user_id",
        lazy="selectin",
    )
