from uuid import UUID

from pydantic import BaseModel, ConfigDict
from app.schemas.permission import PermissionResponse


class RoleResponse(BaseModel):
    """Define the schema for role response.

    Parameters:
        id (type=UUID): Primary identifier for this record.
        name (type=str): Human-readable name for this entity.
        description (type=str | None): Optional human-readable description.
    """
    id: UUID
    name: str
    description: str | None

    model_config = ConfigDict(from_attributes=True)


class RoleWithPermissions(RoleResponse):
    """Define the role with permissions type.

    Parameters:
        permissions (type=list[PermissionResponse]): Permissions associated with the role or response.
    """
    permissions: list[PermissionResponse]


class RoleCreate(BaseModel):
    """Define the schema for role create.

    Parameters:
        name (type=str): Human-readable name for this entity.
        description (type=str | None): Optional human-readable description.
    """
    name: str
    description: str | None = None


class RolePermissionSet(BaseModel):
    """Define the schema for role permission set.

    Parameters:
        permission_keys (type=list[str]): Permission keys value used by this model/schema.
    """
    permission_keys: list[str]


class RoleUpdate(BaseModel):
    """Define the schema for role update.

    Parameters:
        name (type=str | None): Human-readable name for this entity.
        description (type=str | None): Optional human-readable description.
    """
    name: str | None = None
    description: str | None = None
