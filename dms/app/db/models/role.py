from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.db.base import Base
from app.db.models.role_hierarchy import role_hierarchy


class Role(Base):
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
