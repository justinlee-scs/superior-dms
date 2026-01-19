from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    """
    Public-facing document representation.
    Returned by GET /documents/{id} and POST /documents.
    """

    id: UUID
    filename: str
    created_at: datetime

    current_version_id: UUID
    status: str
    classification: Optional[str] = None

    class Config:
        orm_mode = True
