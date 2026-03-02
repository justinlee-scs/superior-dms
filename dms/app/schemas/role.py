from pydantic import BaseModel
from uuid import UUID
from typing import List

from app.schemas.permission import PermissionResponse


class RoleResponse(BaseModel):
    id: UUID
    name: str
    description: str | None

    class Config:
        from_attributes = True


class RoleWithPermissions(RoleResponse):
    permissions: list[PermissionResponse]


class RoleCreate(BaseModel):
    name: str
    description: str | None = None


class RolePermissionSet(BaseModel):
    permission_keys: list[str]


class RoleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
