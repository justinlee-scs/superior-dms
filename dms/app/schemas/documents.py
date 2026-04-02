from datetime import datetime, date
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentResponse(BaseModel):
    """API response model for listing and retrieving document metadata.

    Parameters:
        id (type=UUID): Primary identifier for this record.
        filename (type=str): Original filename for the uploaded document.
        status (type=str | None): Operation status returned to the client.
        document_type (type=str | None): Document type/category assigned to the record.
        confidence (type=float | None): Model confidence score for the classification/output.
        created_at (type=datetime): Timestamp indicating when the record was created.
        current_version_id (type=UUID | None): Identifier of the currently active version.
        version_count (type=int): Number of versions currently stored for the document.
        current_version_number (type=int | None): Ordinal number of the currently active version.
        tags (type=list[str]): Normalized tags associated with the document/version.
        model_config: Model config value used by this model/schema.
    """
    id: UUID
    filename: str
    author: str | None = None
    status: str | None = None
    document_type: str | None = None
    confidence: float | None = None
    created_at: datetime
    current_version_id: UUID | None = None
    version_count: int = 1
    current_version_number: int | None = 1
    tags: list[str] = Field(default_factory=list)
    due_date: date | None = None
    size_bytes: int | None = None
    page_count: int | None = None

    model_config = ConfigDict(from_attributes=True)

class DocumentTypeEnum(str, Enum):
    """Allowed document-type values accepted and returned by the API.

    Parameters:
        statement: Statement value used by this model/schema.
        invoice: Invoice value used by this model/schema.
        outgoing_invoice: Outgoing invoice value used by this model/schema.
        incoming_invoice: Incoming invoice value used by this model/schema.
        contract: Contract value used by this model/schema.
        payroll: Payroll value used by this model/schema.
        manual: Manual value used by this model/schema.
        receipt: Receipt value used by this model/schema.
        other: Other value used by this model/schema.
    """
    statement = "statement"
    invoice = "invoice"
    outgoing_invoice = "outgoing_invoice"
    incoming_invoice = "incoming_invoice"
    contract = "contract"
    payroll = "payroll"
    manual = "manual"
    receipt = "receipt"
    other = "other"


class DocumentCreate(BaseModel):
    """Request payload for creating a new document record.

    Parameters:
        filename (type=str): Original filename for the uploaded document.
        document_type (type=DocumentTypeEnum): Document type/category assigned to the record.
    """
    filename: str
    document_type: DocumentTypeEnum


class DocumentRead(BaseModel):
    """Compact document read model used by endpoints and internal responses.

    Parameters:
        id (type=UUID): Primary identifier for this record.
        filename (type=str): Original filename for the uploaded document.
        document_type (type=DocumentTypeEnum): Document type/category assigned to the record.
        created_at (type=datetime): Timestamp indicating when the record was created.
    """
    id: UUID
    filename: str
    document_type: DocumentTypeEnum
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DocumentTypeUpdate(BaseModel):
    """Request payload for updating a document's type.

    Parameters:
        document_type (type=DocumentTypeEnum): Document type/category assigned to the record.
    """
    document_type: DocumentTypeEnum


class BulkDownloadRequest(BaseModel):
    """Request payload for downloading multiple current document versions as a ZIP."""

    document_ids: list[UUID] = Field(min_length=1, max_length=100)


class DuePaymentItem(BaseModel):
    """Upcoming due payment item derived from incoming invoices."""

    document_id: UUID
    version_id: UUID
    filename: str
    due_date: date
