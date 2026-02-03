from pydantic import BaseModel
from uuid import UUID
from typing import List

from app.schemas.role import RoleResponse


class UserResponse(BaseModel):
    id: UUID
    email: str
    is_active: bool
    roles: list[RoleResponse]

    class Config:
        from_attributes = True
