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
