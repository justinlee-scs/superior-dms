from pydantic import BaseModel
from pydantic import EmailStr
from uuid import UUID
from typing import List

from app.schemas.role import RoleResponse
from app.db.models.user_permission_override import PermissionEffect


class UserResponse(BaseModel):
    id: UUID
    username: str
    email: str
    is_active: bool
    roles: list[RoleResponse]

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    is_active: bool = True


class UserRoleSet(BaseModel):
    role_ids: list[UUID]


class PermissionOverrideInput(BaseModel):
    permission_key: str
    effect: PermissionEffect


class UserOverrideSet(BaseModel):
    overrides: list[PermissionOverrideInput]
