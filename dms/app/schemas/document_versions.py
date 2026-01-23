from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from app.db.models.enums import ProcessingStatus


class DocumentVersionResponse(BaseModel):
    id: UUID
    document_id: UUID
    processing_status: ProcessingStatus
    extracted_text: str | None
    classification: str | None
    confidence: float | None
    created_at: datetime

    class Config:
        from_attributes = True
