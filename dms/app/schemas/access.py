from pydantic import BaseModel
from typing import set


class EffectivePermissionsResponse(BaseModel):
    permissions: set[str]
