from pydantic import BaseModel
from uuid import UUID


class PermissionResponse(BaseModel):
    id: UUID
    key: str
    description: str | None

    class Config:
        from_attributes = True
