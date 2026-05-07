from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr
from app.schemas.role import RoleResponse
from app.db.models.user_permission_override import PermissionEffect


class UserResponse(BaseModel):
    """Define the schema for user response.

    Parameters:
        id (type=UUID): Primary identifier for this record.
        username (type=str): Unique username used to identify the user.
        email (type=str): User email address used for login and contact.
        is_active (type=bool): Whether the user account or entity is active.
        roles (type=list[RoleResponse]): Roles assigned to the user.
        auth_provider (type=str): Authentication source for this user (e.g., local, google).
        oidc_subject (type=str | None): OIDC subject claim linked to this account, when present.
    """
    id: UUID
    username: str
    email: str
    is_active: bool
    roles: list[RoleResponse]
    auth_provider: str
    oidc_subject: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    """Define the schema for user create.

    Parameters:
        username (type=str): Unique username used to identify the user.
        email (type=EmailStr): User email address used for login and contact.
        password (type=str): Password value used by this model/schema.
        is_active (type=bool): Whether the user account or entity is active.
    """
    username: str
    email: EmailStr
    password: str
    is_active: bool = True


class UserRoleSet(BaseModel):
    """Define the schema for user role set.

    Parameters:
        role_ids (type=list[UUID]): Role identifiers to assign to the user.
    """
    role_ids: list[UUID]


class PermissionOverrideInput(BaseModel):
    """Define the schema for permission override input.

    Parameters:
        permission_key (type=str): Permission key the override applies to.
        effect (type=PermissionEffect): Override effect determining whether access is allowed or denied.
    """
    permission_key: str
    effect: PermissionEffect


class UserOverrideSet(BaseModel):
    """Define the schema for user override set.

    Parameters:
        overrides (type=list[PermissionOverrideInput]): Collection of permission overrides to apply.
    """
    overrides: list[PermissionOverrideInput]


class UserPasswordSet(BaseModel):
    new_password: str
