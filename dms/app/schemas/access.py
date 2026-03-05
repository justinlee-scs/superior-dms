from pydantic import BaseModel


class EffectivePermissionsResponse(BaseModel):
    """Define the schema for effective permissions response.

    Parameters:
        permissions (type=set[str]): Permissions associated with the role or response.
    """
    permissions: set[str]
