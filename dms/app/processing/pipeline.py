import os
import logging
from sqlalchemy.orm import Session

from app.db.models.document_versions import DocumentVersion
from app.db.models.enums import ProcessingStatus, DocumentClass
from app.db.models.documents import DocumentType
from app.db.repositories.documents import list_existing_tags
from app.db.repositories.tags import create_tag_pool_entry

from app.services.extraction.handwriting import is_handwritten
from app.services.extraction.icr import run_icr_model
from app.services.extraction.classify import classify_document
from app.services.extraction.tags import derive_tags
from app.services.extraction.due_dates import extract_due_date
from app.services.extraction.field_extractor import extract_fields, fields_to_tags

from app.services.extraction.ocr_sync import extract_text_with_metadata
from app.services.labelstudio.client import LabelStudioClient, LabelStudioConfig

logger = logging.getLogger(__name__)


def _label_studio_enabled() -> bool:
    return os.getenv("LABEL_STUDIO_ENABLED", "false").strip().lower() in {"1", "true", "yes"}


def _notify_label_studio(*, document_id: str, filename: str, text: str) -> None:
    if not _label_studio_enabled():
        return
    base_url = os.getenv("LABEL_STUDIO_URL", "").strip()
    api_token = os.getenv("LABEL_STUDIO_API_TOKEN", "").strip()
    project_id = int(os.getenv("LABEL_STUDIO_PROJECT_ID", "0") or "0")
    if not base_url or not api_token or project_id <= 0:
        logger.warning("Label Studio config missing; skipping export.")
        return
    client = LabelStudioClient(
        LabelStudioConfig(
            base_url=base_url.rstrip("/"),
            api_token=api_token,
            project_id=project_id,
        )
    )
    try:
        client.create_task_for_document(doc_id=document_id, filename=filename, text=text)
    except Exception as exc:
        logger.warning("Label Studio export failed: %s", exc)

def process_document(
    db: Session,
    version_id: str,
    file_bytes: bytes,
    *,
    commit: bool = True,
) -> None:
    """Process document.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        version_id (type=str): Identifier used to locate the target record.
        file_bytes (type=bytes): Raw file content used for validation or processing.
        commit (type=bool, default=True): Flag controlling whether to commit the transaction.
    """
    version = (
        db.query(DocumentVersion)
        .filter(DocumentVersion.id == version_id)
        .one_or_none()
    )

    if not version:
        return

    try:
        extraction = extract_text_with_metadata(
            file_bytes=file_bytes,
            filename=version.document.filename,
        )
        text = extraction.text
        confidence = extraction.confidence

        classification = classify_document(text)
        existing_tags = list_existing_tags(db)
        tags = derive_tags(
            text,
            classification,
            document_type=version.document.document_type,
            filename=version.document.filename,
            existing_tags=existing_tags,
        )
        field_values = extract_fields(file_bytes, version.document.filename)
        if field_values:
            tags.extend(fields_to_tags(field_values))
        due_date = None
        if classification == DocumentClass.INCOMING_INVOICE:
            due_date = extract_due_date(text)
        if version.document.document_type == DocumentType.incoming_invoice:
            due_date = due_date or extract_due_date(text)
        if due_date:
            tags.append(f"due_date:{due_date.isoformat()}")
        page_count = extraction.metadata.get("page_count")
        if page_count is None:
            page_count = extraction.metadata.get("pages")
        if isinstance(page_count, str) and page_count.isdigit():
            page_count = int(page_count)
        if isinstance(page_count, (float, int)):
            page_count = int(page_count)
        else:
            page_count = None
        handwriting_conf = extraction.metadata.get("handwriting_confidence")
        needs_review = False
        if handwriting_conf is not None and handwriting_conf < 0.85:
            needs_review = True
        required_prefixes = ("company:", "project:", "document_type:")
        for prefix in required_prefixes:
            if not any(tag.startswith(prefix) for tag in tags):
                needs_review = True
                break
        if needs_review:
            tags.append("needs_review")
        for tag in tags:
            try:
                create_tag_pool_entry(db=db, tag=tag)
            except ValueError:
                continue

        version.extracted_text = text
        version.classification = classification
        version.confidence = confidence
        version.ocr_raw_confidence = extraction.raw_confidence
        version.ocr_engine = extraction.engine
        version.ocr_model_version = extraction.model_version
        version.ocr_latency_ms = extraction.latency_ms
        version.tags = tags
        version.due_date = due_date
        version.page_count = page_count
        if version.storage_size_bytes is None and file_bytes is not None:
            version.storage_size_bytes = len(file_bytes)
        version.processing_status = ProcessingStatus.uploaded
        _notify_label_studio(
            document_id=str(version.document_id),
            filename=version.document.filename,
            text=text,
        )

    except Exception:
        version.processing_status = ProcessingStatus.failed
        if commit:
            db.commit()
        else:
            db.flush()
        raise

    if commit:
        db.commit()
    else:
        db.flush()
