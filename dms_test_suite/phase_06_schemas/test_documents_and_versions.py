import uuid
from datetime import datetime, timezone

from app.db.models.enums import ProcessingStatus
from app.schemas.document_versions import DocumentVersionListItem, DocumentVersionResponse
from app.schemas.documents import DocumentResponse, DocumentTypeEnum, DocumentTypeUpdate


def test_document_response_defaults() -> None:
    now = datetime.now(timezone.utc)
    doc = DocumentResponse(
        id=uuid.uuid4(),
        filename="invoice.pdf",
        created_at=now,
    )

    assert doc.version_count == 1
    assert doc.current_version_number == 1
    assert doc.status is None
    assert doc.document_type is None


def test_document_type_update_uses_enum() -> None:
    payload = DocumentTypeUpdate(document_type=DocumentTypeEnum.contract)
    assert payload.document_type == DocumentTypeEnum.contract


def test_document_version_response_defaults() -> None:
    now = datetime.now(timezone.utc)
    item = DocumentVersionResponse(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        processing_status=ProcessingStatus.uploaded,
        extracted_text=None,
        classification=None,
        confidence=None,
        created_at=now,
    )

    assert item.tags == []
    assert item.ocr_engine is None
    assert item.ocr_model_version is None
    assert item.ocr_latency_ms is None


def test_document_version_list_item_builds_with_required_fields() -> None:
    now = datetime.now(timezone.utc)
    item = DocumentVersionListItem(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        version_number=3,
        is_current=True,
        processing_status=ProcessingStatus.processing,
        classification="invoice",
        confidence=0.88,
        created_at=now,
        size_bytes=2048,
    )

    assert item.version_number == 3
    assert item.tags == []
