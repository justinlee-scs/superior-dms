from pydantic import BaseModel


class EffectivePermissionsResponse(BaseModel):
    permissions: set[str]
