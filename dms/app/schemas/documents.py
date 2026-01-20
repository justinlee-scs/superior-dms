from datetime import datetime
from typing import Optional
from uuid import UUID
from enum import Enum
from datetime import datetime 

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: UUID
    filename: str
    status: str | None = None
    document_type: str | None = None
    confidence: float | None = None
    created_at: datetime
    current_version_id: UUID | None = None

    model_config = {
        "from_attributes": True
    }

class DocumentTypeEnum(str, Enum):
    statement = "statement"
    outgoing_invoice = "outgoing_invoice"
    incoming_invoice = "incoming_invoice"
    contract = "contract"
    payroll = "payroll"
    manual = "manual"
    receipt = "receipt"
    other = "other"


class DocumentCreate(BaseModel):
    filename: str
    document_type: DocumentTypeEnum


class DocumentRead(BaseModel):
    id: UUID
    filename: str
    document_type: DocumentTypeEnum
    created_at: datetime

    class Config:
        from_attributes = True

class DocumentTypeUpdate(BaseModel):
    document_type: DocumentTypeEnum