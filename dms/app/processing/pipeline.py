from marshal import version
import os
import logging
from pathlib import Path
from sqlalchemy.orm import Session

from app.db.models.document_versions import DocumentVersion
from app.db.models.enums import ProcessingStatus, DocumentClass
from app.db.models.documents import DocumentType
from app.db.repositories.documents import list_existing_tags
from app.db.repositories.tags import create_tag_pool_entry

from app.services.extraction.handwriting import is_handwritten
from app.services.extraction.icr import run_icr_model
from app.services.extraction.classify import classify_document
from app.services.extraction.tags import derive_tags, normalize_tag
from app.services.extraction.due_dates import extract_due_date
from app.services.extraction.field_extractor import extract_fields, fields_to_tags
from app.services.extraction.lilt import run_lilt_model

from app.services.extraction.ocr_sync import extract_text_with_metadata
from app.services.labelstudio.client import LabelStudioClient, LabelStudioConfig

logger = logging.getLogger(__name__)

_LILT_IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".tif",
    ".tiff",
    ".bmp",
    ".gif",
    ".webp",
    ".pdf",
    ".avif",
}


def _can_run_lilt(filename: str | None) -> bool:
    suffix = Path(filename or "").suffix.lower()
    return suffix in _LILT_IMAGE_EXTENSIONS


def _lilt_company_tag_strict() -> bool:
    return os.getenv("LILT_COMPANY_TAG_STRICT", "true").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def _extract_company_tag_from_fields(fields: dict[str, object] | None) -> str | None:
    if not fields:
        return None

    preferred_keys = (
        "vendor",
        "vendor_name",
        "supplier",
        "supplier_name",
        "company",
        "company_name",
        "bill_to",
    )

    normalized_map: dict[str, str] = {}
    for key, raw_value in fields.items():
        key_norm = str(key).strip().lower().replace(" ", "_")
        value = str(raw_value or "").strip()
        if not value:
            continue
        normalized_map[key_norm] = value

    for key in preferred_keys:
        if key in normalized_map:
            tag = normalize_tag(f"company:{normalized_map[key]}")
            if tag and tag != "company:":
                return tag

    return None


def _label_studio_enabled() -> bool:
    return os.getenv("LABEL_STUDIO_ENABLED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
    }


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
        client.create_task_for_document(
            doc_id=document_id, filename=filename, text=text
        )
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
        db.query(DocumentVersion).filter(DocumentVersion.id == version_id).one_or_none()
    )

    if not version:
        return

    try:
        version.processing_status = ProcessingStatus.processing

        # ---- OCR EXTRACTION ----
        extraction = extract_text_with_metadata(
            file_bytes=file_bytes,
            filename=version.document.filename,
        )

        text = extraction.text
        confidence = extraction.confidence

        # ---- LiLT STRUCTURED EXTRACTION (PRIMARY FOR SUPPORTED IMAGES) ----
        lilt_result = None
        lilt_status = "skipped_unsupported_type"
        if _can_run_lilt(version.document.filename):
            try:
                lilt_result = run_lilt_model(
                    file_bytes=file_bytes,
                    filename=version.document.filename,
                )
                lilt_status = "used" if lilt_result else "empty_result"
            except Exception as exc:
                lilt_status = "failed_fallback"
                logger.warning(
                    "LiLT extraction failed for version %s (%s): %s",
                    version.id,
                    version.document.filename,
                    exc,
                )

        # merge LiLT extracted text if available
        if lilt_result and lilt_result.text:
            text = lilt_result.text
            confidence = lilt_result.confidence or confidence

        # ---- CLASSIFICATION ----
        classification = classify_document(text)

        existing_tags = list_existing_tags(db)

        # ---- TAG DERIVATION ----
        derived_tags = set(
            derive_tags(
                text,
                classification,
                document_type=version.document.document_type,
                filename=version.document.filename,
                existing_tags=existing_tags,
            )
        )

        # ---- FIELD EXTRACTION (LiLT PRIORITY) ----
        field_values = None

        if lilt_result and lilt_result.fields:
            field_values = lilt_result.fields
        else:
            field_values = extract_fields(file_bytes, version.document.filename)

        field_tags = set(fields_to_tags(field_values)) if field_values else set()

        new_system_tags = derived_tags.union(field_tags)

        existing_tags_set = set(version.tags or [])
        user_tags = {t for t in existing_tags_set if not t.startswith("system:")}

        tags = sorted(user_tags.union(new_system_tags))

        company_tag_from_lilt = _extract_company_tag_from_fields(
            lilt_result.fields if lilt_result else None
        )
        company_tag_from_fields = _extract_company_tag_from_fields(field_values)

        company_tag_to_apply = company_tag_from_fields
        if _can_run_lilt(version.document.filename) and _lilt_company_tag_strict():
            company_tag_to_apply = company_tag_from_lilt

        if company_tag_to_apply:
            tags = [t for t in tags if not t.startswith("company:")]
            tags.append(company_tag_to_apply)
            tags = sorted(set(tags))

        # ---- DUE DATE ----
        due_date = None
        is_invoice = (
            classification == DocumentClass.INCOMING_INVOICE
            or version.document.document_type == DocumentType.incoming_invoice
        )

        if is_invoice:
            if lilt_result and lilt_result.fields and "due_date" in lilt_result.fields:
                due_date = lilt_result.fields.get("due_date")
            else:
                due_date = extract_due_date(text)

        if due_date:
            tags = [t for t in tags if not t.startswith("due_date:")]
            tags.append(f"due_date:{due_date.isoformat()}")

        # ---- PAGE COUNT ----
        page_count = extraction.metadata.get("page_count")
        if page_count is None:
            page_count = extraction.metadata.get("pages")

        if isinstance(page_count, str) and page_count.isdigit():
            page_count = int(page_count)
        elif isinstance(page_count, (float, int)):
            page_count = int(page_count)
        else:
            page_count = None

        # ---- REVIEW FLAG ----
        needs_review = False

        if confidence is not None and confidence < 0.75:
            needs_review = True

        required_prefixes = ("company:", "project:", "document_type:")
        for prefix in required_prefixes:
            if not any(tag.startswith(prefix) for tag in tags):
                needs_review = True
                break

        if needs_review:
            tags.append("needs_review")

        if (
            _can_run_lilt(version.document.filename)
            and _lilt_company_tag_strict()
            and not company_tag_from_lilt
        ):
            tags.append("lilt_company_missing")
            if "needs_review" not in tags:
                tags.append("needs_review")

        # ---- TAG POOL ----
        for tag in tags:
            try:
                create_tag_pool_entry(db=db, tag=tag)
            except ValueError:
                continue

        # ---- ASSIGN ----
        version.extracted_text = text
        version.classification = classification
        version.confidence = confidence
        version.ocr_raw_confidence = extraction.raw_confidence
        version.ocr_engine = "lilt+ocr"
        version.ocr_model_version = "lilt"
        version.ocr_latency_ms = extraction.latency_ms

        version.tags = list(tags)
        version.due_date = due_date
        version.page_count = page_count

        if version.storage_size_bytes is None and file_bytes is not None:
            version.storage_size_bytes = len(file_bytes)

        version.processing_status = ProcessingStatus.uploaded
        logger.info(
            "Document processed version_id=%s filename=%s status=%s lilt=%s lilt_company_tag=%s classification=%s confidence=%s tags=%s company_tag=%s",
            version.id,
            version.document.filename,
            version.processing_status.value,
            lilt_status,
            company_tag_from_lilt or "",
            (
                classification.value
                if hasattr(classification, "value")
                else classification
            ),
            confidence,
            len(tags),
            next((t for t in tags if t.startswith("company:")), ""),
        )

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
