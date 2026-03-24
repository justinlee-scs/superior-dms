from uuid import UUID

from pydantic import BaseModel, ConfigDict

class PermissionResponse(BaseModel):
    """Define the schema for permission response.

    Parameters:
        id (type=UUID): Primary identifier for this record.
        key (type=str): Unique permission key used in authorization checks.
        description (type=str | None): Optional human-readable description.
    """
    id: UUID
    key: str
    description: str | None

    model_config = ConfigDict(from_attributes=True)
