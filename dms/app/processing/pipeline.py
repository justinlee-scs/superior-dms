from marshal import version
import os
import logging
from pathlib import Path
from sqlalchemy.orm import Session

from app.db.models.document_versions import DocumentVersion
from app.db.models.enums import ProcessingStatus, DocumentClass
from app.db.models.documents import DocumentType
from app.db.repositories.documents import list_existing_tags, list_rejected_tags
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

_INVOICE_REQUIRED_TAGS = (
    "vendor",
    "document_date",
    "payment_due_date",
    "grand_total",
    "invoice_number",
)


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


def _is_invoice_classification(classification: DocumentClass | None) -> bool:
    return classification in {
        DocumentClass.INCOMING_INVOICE,
        DocumentClass.OUTGOING_INVOICE,
    }


def _is_invoice_doc_type(document_type: DocumentType | None) -> bool:
    return document_type in {
        DocumentType.incoming_invoice,
        DocumentType.outgoing_invoice,
    }


def _has_prefixed_tag(tags: list[str], prefix: str) -> bool:
    return any(tag.startswith(f"{prefix}:") for tag in tags)


def _ensure_invoice_required_tags(tags: list[str]) -> tuple[list[str], list[str]]:
    """Normalize invoice tags and return (normalized_tags, missing_required_fields)."""
    normalized = list(tags)

    # Normalize legacy/alternate prefixes to required invoice schema.
    # company:* -> vendor:*
    vendor_from_company = next(
        (t.split(":", 1)[1] for t in normalized if t.startswith("company:")),
        None,
    )
    if vendor_from_company and not _has_prefixed_tag(normalized, "vendor"):
        normalized.append(f"vendor:{vendor_from_company}")

    # due_date:* -> payment_due_date:*
    payment_due_from_due_date = next(
        (t.split(":", 1)[1] for t in normalized if t.startswith("due_date:")),
        None,
    )
    if payment_due_from_due_date and not _has_prefixed_tag(normalized, "payment_due_date"):
        normalized.append(f"payment_due_date:{payment_due_from_due_date}")

    missing = [
        key for key in _INVOICE_REQUIRED_TAGS if not _has_prefixed_tag(normalized, key)
    ]
    return sorted(set(normalized)), missing


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
        logger.info(
            "Pipeline start version_id=%s filename=%s", version.id, version.document.filename
        )
        version.processing_status = ProcessingStatus.processing
        rejected_tags = set(list_rejected_tags(db))

        # ---- OCR EXTRACTION ----
        logger.info("Pipeline stage=ocr_start version_id=%s", version.id)
        extraction = extract_text_with_metadata(
            file_bytes=file_bytes,
            filename=version.document.filename,
        )
        logger.info(
            "Pipeline stage=ocr_done version_id=%s latency_ms=%s page_count=%s",
            version.id,
            extraction.latency_ms,
            extraction.metadata.get("page_count") or extraction.metadata.get("pages"),
        )

        text = extraction.text
        confidence = extraction.confidence

        # ---- LiLT STRUCTURED EXTRACTION (PRIMARY FOR SUPPORTED IMAGES) ----
        lilt_result = None
        lilt_status = "skipped_unsupported_type"
        if _can_run_lilt(version.document.filename):
            try:
                logger.info("Pipeline stage=lilt_start version_id=%s", version.id)
                lilt_result = run_lilt_model(
                    file_bytes=file_bytes,
                    filename=version.document.filename,
                )
                lilt_status = "used" if lilt_result else "empty_result"
                logger.info(
                    "Pipeline stage=lilt_done version_id=%s status=%s",
                    version.id,
                    lilt_status,
                )
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
        logger.info("Pipeline stage=classification_start version_id=%s", version.id)
        classification = classify_document(text)
        logger.info(
            "Pipeline stage=classification_done version_id=%s classification=%s",
            version.id,
            classification.value if hasattr(classification, "value") else classification,
        )

        existing_tags = [tag for tag in list_existing_tags(db) if tag not in rejected_tags]

        # ---- TAG DERIVATION ----
        logger.info("Pipeline stage=tag_derivation_start version_id=%s", version.id)
        derived_tags = set(
            derive_tags(
                text,
                classification,
                document_type=version.document.document_type,
                filename=version.document.filename,
                existing_tags=existing_tags,
            )
        ) - rejected_tags

        # ---- FIELD EXTRACTION (LiLT PRIORITY) ----
        logger.info("Pipeline stage=field_extraction_start version_id=%s", version.id)
        field_values = None

        if lilt_result and lilt_result.fields:
            field_values = lilt_result.fields
        else:
            field_values = extract_fields(file_bytes, version.document.filename)
        logger.info(
            "Pipeline stage=field_extraction_done version_id=%s has_fields=%s",
            version.id,
            bool(field_values),
        )

        field_tags = set(fields_to_tags(field_values)) if field_values else set()
        field_tags -= rejected_tags

        new_system_tags = derived_tags.union(field_tags)

        existing_tags_set = set(version.tags or [])
        user_tags = {t for t in existing_tags_set if not t.startswith("system:")}

        tags = sorted(user_tags.union(new_system_tags) - rejected_tags)

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
        logger.info("Pipeline stage=due_date_start version_id=%s", version.id)
        due_date = None
        is_invoice = _is_invoice_classification(classification) or _is_invoice_doc_type(
            version.document.document_type
        )

        if is_invoice:
            if lilt_result and lilt_result.fields and "due_date" in lilt_result.fields:
                due_date = lilt_result.fields.get("due_date")
            else:
                due_date = extract_due_date(text)

        if due_date:
            tags = [t for t in tags if not t.startswith("due_date:")]
            tags.append(f"due_date:{due_date.isoformat()}")
            if not any(t.startswith("payment_due_date:") for t in tags):
                tags.append(f"payment_due_date:{due_date.isoformat()}")
        logger.info(
            "Pipeline stage=due_date_done version_id=%s due_date=%s",
            version.id,
            due_date.isoformat() if due_date else "",
        )

        # ---- PAGE COUNT ----
        logger.info("Pipeline stage=page_count_start version_id=%s", version.id)
        page_count = extraction.metadata.get("page_count")
        if page_count is None:
            page_count = extraction.metadata.get("pages")

        if isinstance(page_count, str) and page_count.isdigit():
            page_count = int(page_count)
        elif isinstance(page_count, (float, int)):
            page_count = int(page_count)
        else:
            page_count = None
        logger.info(
            "Pipeline stage=page_count_done version_id=%s page_count=%s",
            version.id,
            page_count,
        )

        # ---- REVIEW FLAG ----
        logger.info("Pipeline stage=review_flag_start version_id=%s", version.id)
        needs_review = False

        if confidence is not None and confidence < 0.75:
            needs_review = True

        required_prefixes = ("company:", "project:", "document_type:")
        for prefix in required_prefixes:
            if not any(tag.startswith(prefix) for tag in tags):
                needs_review = True
                break

        if is_invoice:
            tags, missing_invoice_fields = _ensure_invoice_required_tags(tags)
            if missing_invoice_fields:
                needs_review = True

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
        logger.info(
            "Pipeline stage=review_flag_done version_id=%s needs_review=%s",
            version.id,
            needs_review,
        )

        # ---- TAG POOL ----
        logger.info("Pipeline stage=tag_pool_start version_id=%s", version.id)
        for tag in tags:
            try:
                create_tag_pool_entry(db=db, tag=tag)
            except ValueError:
                continue
        logger.info("Pipeline stage=tag_pool_done version_id=%s", version.id)

        # ---- ASSIGN ----
        logger.info("Pipeline stage=assign_start version_id=%s", version.id)
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
            "Pipeline stage=assign_done version_id=%s status=%s tags=%s",
            version.id,
            version.processing_status.value,
            len(tags),
        )
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
        logger.info("Pipeline stage=label_studio_done version_id=%s", version.id)

    except Exception:
        version.processing_status = ProcessingStatus.failed
        if commit:
            db.commit()
        else:
            db.flush()
        logger.exception("Pipeline failed version_id=%s", version.id)
        raise

    if commit:
        db.commit()
    else:
        db.flush()
    logger.info("Pipeline commit_complete version_id=%s", version.id)
