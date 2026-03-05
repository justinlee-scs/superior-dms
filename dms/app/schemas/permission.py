from pydantic import BaseModel
from uuid import UUID


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

    class Config:
        """Configure model serialization and ORM behavior.

        Parameters:
            from_attributes: Enable model construction from ORM attributes.
        """
        from_attributes = True
