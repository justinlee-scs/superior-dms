from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from app.db.models.enums import ProcessingStatus


class DocumentVersionResponse(BaseModel):
    """Define the schema for document version response.

    Parameters:
        id (type=UUID): Primary identifier for this record.
        document_id (type=UUID): Identifier of the parent document.
        processing_status (type=ProcessingStatus): Current processing state for this document version.
        extracted_text (type=str | None): Extracted plain text generated from OCR/parsing.
        classification (type=str | None): Predicted document class label.
        confidence (type=float | None): Model confidence score for the classification/output.
        ocr_raw_confidence (type=float | None): Raw OCR confidence score from the extraction engine.
        ocr_engine (type=str | None): Name of the OCR engine used for extraction.
        ocr_model_version (type=str | None): Version string of the OCR model used.
        ocr_latency_ms (type=int | None): OCR processing latency in milliseconds.
        tags (type=list[str]): Normalized tags associated with the document/version.
        created_at (type=datetime): Timestamp indicating when the record was created.
    """
    id: UUID
    document_id: UUID
    processing_status: ProcessingStatus
    extracted_text: str | None
    classification: str | None
    confidence: float | None
    ocr_raw_confidence: float | None = None
    ocr_engine: str | None = None
    ocr_model_version: str | None = None
    ocr_latency_ms: int | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentVersionListItem(BaseModel):
    """Define the schema for document version list item.

    Parameters:
        id (type=UUID): Primary identifier for this record.
        document_id (type=UUID): Identifier of the parent document.
        version_number (type=int): Ordinal number for this version within its document history.
        is_current (type=bool): Whether this version is currently active for the document.
        processing_status (type=ProcessingStatus): Current processing state for this document version.
        classification (type=str | None): Predicted document class label.
        confidence (type=float | None): Model confidence score for the classification/output.
        ocr_engine (type=str | None): Name of the OCR engine used for extraction.
        ocr_model_version (type=str | None): Version string of the OCR model used.
        tags (type=list[str]): Normalized tags associated with the document/version.
        created_at (type=datetime): Timestamp indicating when the record was created.
        size_bytes (type=int): File size of the version in bytes.
    """
    id: UUID
    document_id: UUID
    version_number: int
    is_current: bool
    processing_status: ProcessingStatus
    classification: str | None
    confidence: float | None
    ocr_engine: str | None = None
    ocr_model_version: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    size_bytes: int


class SetCurrentVersionResponse(BaseModel):
    """Define the schema for set current version response.

    Parameters:
        status (type=str): Operation status returned to the client.
        document_id (type=UUID): Identifier of the parent document.
        current_version_id (type=UUID): Identifier of the currently active version.
    """
    status: str
    document_id: UUID
    current_version_id: UUID
