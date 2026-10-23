import logging
import os
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.models.document_versions import DocumentVersion
from app.db.models.documents import DocumentType
from app.db.models.enums import DocumentClass, ProcessingStatus
from app.db.models.ocr_correction import OCRCorrectionQueue, OCRWordBox, CorrectionStatus
from app.db.repositories.documents import list_existing_tags, list_rejected_tags
from app.db.repositories.tags import create_tag_pool_entry
from app.services.extraction.classify import classify_document
from app.services.extraction.due_dates import extract_due_date, parse_date_value
from app.services.extraction.doctr_engine import run_doctr_extraction
from app.services.extraction.field_extractor import (
    extract_fields,
    fields_to_tags,
    normalize_extracted_fields,
)
from app.services.extraction.handwriting import is_handwritten
from app.services.extraction.icr import run_icr_model
from app.services.extraction.tags import derive_tags, normalize_tag
from app.services.extraction.ocr_sync import extract_text_with_metadata

logger = logging.getLogger(__name__)

_OCR_IMAGE_EXTENSIONS = {
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
    "grand_total",
    "invoice_number",
)


def _supports_document_ocr(filename: str | None) -> bool:
    suffix = Path(filename or "").suffix.lower()
    return suffix in _OCR_IMAGE_EXTENSIONS


def _prefer_doctr_vendor_tag() -> bool:
    setting = os.getenv("DOCTR_VENDOR_TAG_STRICT", os.getenv("DOCTR_COMPANY_TAG_STRICT", "true"))
    return setting.strip().lower() in {
        "1",
        "true",
        "yes",
    }


def _extract_vendor_tag(fields: dict[str, object] | None) -> str | None:
    if not fields:
        return None

    preferred_keys = (
        "vendor",
        "vendor_name",
        "supplier",
        "supplier_name",
        "company",
        "company_name",
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
            tag = normalize_tag(f"vendor:{normalized_map[key]}")
            if tag and tag != "vendor:":
                return tag

    return None


def _is_invoice_classification_result(classification: DocumentClass | None) -> bool:
    return classification in {
        DocumentClass.INCOMING_INVOICE,
        DocumentClass.OUTGOING_INVOICE,
    }


def _is_invoice_document_type(document_type: DocumentType | None) -> bool:
    return document_type in {
        DocumentType.incoming_invoice,
        DocumentType.outgoing_invoice,
    }


def _has_tag_with_prefix(tags: list[str], prefix: str) -> bool:
    return any(tag.startswith(f"{prefix}:") for tag in tags)


def _normalize_invoice_required_tags(tags: list[str]) -> tuple[list[str], list[str]]:
    """Normalize invoice tags and return (normalized_tags, missing_required_fields)."""
    normalized = list(tags)

    normalized = [
        f"vendor:{tag.split(':', 1)[1]}" if tag.startswith("company:") else tag
        for tag in normalized
    ]

    missing = [
        key for key in _INVOICE_REQUIRED_TAGS if not _has_tag_with_prefix(normalized, key)
    ]
    return sorted(set(normalized)), missing


def process_document_version(
    db: Session,
    version_id: str,
    file_bytes: bytes,
    *,
    commit: bool = True,
) -> None:
    """Process a document version through OCR, extraction, and tagging."""
    version = (
        db.query(DocumentVersion).filter(DocumentVersion.id == version_id).one_or_none()
    )

    if not version:
        return

    try:
        logger.info(
            "Pipeline start version_id=%s filename=%s",
            version.id,
            version.document.filename,
        )
        version.processing_status = ProcessingStatus.processing
        rejected_tags = set(list_rejected_tags(db))

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

        # ---- DocTR STRUCTURED EXTRACTION (PRIMARY FOR SUPPORTED IMAGES) ----
        doctr_result = None
        doctr_status = "skipped_unsupported_type"
        if _supports_document_ocr(version.document.filename):
            # No try/except here on purpose. Zero tolerance means a DocTR
            # failure on a supported file type fails the whole document -
            # it propagates to the outer try/except in this function,
            # which marks processing_status=failed and re-raises. A
            # silent fallback to plain OCR (no field extraction, no
            # confidence data) contradicts the "perfect source-of-truth
            # data" requirement: nobody would know it happened.
            logger.info("Pipeline stage=doctr_start version_id=%s", version.id)
            doctr_result = run_doctr_extraction(
                file_bytes=file_bytes,
                filename=version.document.filename,
            )
            doctr_status = "used" if doctr_result else "empty_result"
            logger.info(
                "Pipeline stage=doctr_done version_id=%s status=%s",
                version.id,
                doctr_status,
            )

        if doctr_result and doctr_result.text:
            text = doctr_result.text
            confidence = doctr_result.confidence or confidence

        # ---- OCR CONFIDENCE TRACKING + CORRECTION QUEUE ----
        # DocTR gives per-word confidence that OCR/field_extractor never
        # did. Zero tolerance: ANY word below threshold (set in
        # doctr_engine.py) flags the whole document into the queue.
        logger.info("Pipeline stage=confidence_tracking_start version_id=%s", version.id)

        version.ocr_meta = {
            **(version.ocr_meta or {}),
            "confidence_average": getattr(doctr_result, "ocr_confidence_average", None) if doctr_result else None,
            "confidence_lowest": getattr(doctr_result, "ocr_confidence_lowest", None) if doctr_result else None,
            "low_confidence": bool(getattr(doctr_result, "ocr_low_confidence", False)) if doctr_result else False,
            "processing_log": getattr(doctr_result, "processing_log", None) if doctr_result else None,
        }

        if doctr_result and getattr(doctr_result, "extraction_raw_jsonb", None):
            version.extraction_raw = doctr_result.extraction_raw_jsonb
        if doctr_result and doctr_result.fields:
            version.extraction = normalize_extracted_fields(doctr_result.fields)

        logger.info(
            "Pipeline stage=confidence_tracking_done version_id=%s low_confidence=%s",
            version.id,
            (version.ocr_meta or {}).get("low_confidence"),
        )

        logger.info("Pipeline stage=classification_start version_id=%s", version.id)
        classification = classify_document(text)
        logger.info(
            "Pipeline stage=classification_done version_id=%s classification=%s",
            version.id,
            classification.value if hasattr(classification, "value") else classification,
        )

        existing_tags = [tag for tag in list_existing_tags(db) if tag not in rejected_tags]

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

        logger.info("Pipeline stage=field_extraction_start version_id=%s", version.id)
        field_values = None

        if doctr_result and doctr_result.fields:
            field_values = normalize_extracted_fields(doctr_result.fields)
        else:
            field_values = normalize_extracted_fields(
                extract_fields(file_bytes, version.document.filename)
            )
        logger.info(
            "Pipeline stage=field_extraction_done version_id=%s has_fields=%s",
            version.id,
            bool(field_values),
        )

        field_tags = set(fields_to_tags(field_values)) if field_values else set()
        field_tags -= rejected_tags

        new_system_tags = derived_tags.union(field_tags)

        existing_tags_set = set(version.document.label_tags or [])
        existing_vendor_tags = {t for t in existing_tags_set if t.startswith("vendor:")}
        user_tags = {t for t in existing_tags_set if not t.startswith(("system:", "company:"))}
        if not existing_vendor_tags:
            user_tags.update(
                "vendor:" + t.split(":", 1)[1]
                for t in existing_tags_set
                if t.startswith("company:")
            )

        tags = sorted(user_tags.union(new_system_tags) - rejected_tags)

        vendor_tag_from_doctr = _extract_vendor_tag(
            normalize_extracted_fields(doctr_result.fields) if doctr_result else None
        )
        vendor_tag_from_fields = _extract_vendor_tag(field_values)

        vendor_tag_to_apply = vendor_tag_from_fields
        if _supports_document_ocr(version.document.filename) and _prefer_doctr_vendor_tag():
            vendor_tag_to_apply = vendor_tag_from_doctr

        if vendor_tag_to_apply:
            tags = [t for t in tags if not t.startswith(("company:", "vendor:"))]
            tags.append(vendor_tag_to_apply)
            tags = sorted(set(tags))

        logger.info("Pipeline stage=due_date_start version_id=%s", version.id)
        due_date = None
        is_invoice = _is_invoice_classification_result(
            classification
        ) or _is_invoice_document_type(version.document.document_type)

        if is_invoice:
            extracted_due_date = (
                doctr_result.fields.get("due_date")
                if doctr_result and doctr_result.fields
                else None
            )
            due_date = parse_date_value(extracted_due_date)
            if due_date is None:
                # Ollama returns JSON strings; only persist valid dates and
                # fall back to the explicit OCR-text parser when needed.
                due_date = extract_due_date(text)

        # Date is stored once on documents.due_date and edited with the
        # calendar control; strip legacy/model-generated date labels.
        tags = [
            t for t in tags
            if not t.startswith("due_date:")
            and not t.startswith("payment_due_date:")
        ]
        logger.info(
            "Pipeline stage=due_date_done version_id=%s due_date=%s",
            version.id,
            due_date.isoformat() if due_date else "",
        )

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

        logger.info("Pipeline stage=review_flag_start version_id=%s", version.id)
        needs_review = False

        if confidence is not None and confidence < 0.75:
            needs_review = True

        required_prefixes = ("vendor:", "project:", "document_type:")
        for prefix in required_prefixes:
            if not any(tag.startswith(prefix) for tag in tags):
                needs_review = True
                break

        if is_invoice:
            tags, missing_invoice_fields = _normalize_invoice_required_tags(tags)
            if due_date is None:
                missing_invoice_fields.append("due_date")
            if missing_invoice_fields:
                needs_review = True

        if needs_review:
            tags.append("needs_review")

        if (
            _supports_document_ocr(version.document.filename)
            and _prefer_doctr_vendor_tag()
            and not vendor_tag_from_doctr
        ):
            tags.append("doctr_vendor_missing")
            if "needs_review" not in tags:
                tags.append("needs_review")
        logger.info(
            "Pipeline stage=review_flag_done version_id=%s needs_review=%s",
            version.id,
            needs_review,
        )

        logger.info("Pipeline stage=tag_pool_start version_id=%s", version.id)
        for tag in tags:
            try:
                create_tag_pool_entry(db=db, tag=tag)
            except ValueError:
                continue
        logger.info("Pipeline stage=tag_pool_done version_id=%s", version.id)

        logger.info("Pipeline stage=assign_start version_id=%s", version.id)
        version.extracted_text = text
        version.ocr_meta = {
            **(version.ocr_meta or {}),
            "confidence": confidence,
            "raw_confidence": extraction.raw_confidence,
            "engine": doctr_result.engine if doctr_result else "ocr_only",
            "model_version": doctr_result.engine_meta.get("recognition_arch", "unknown") if doctr_result else "none",
            "latency_ms": extraction.latency_ms,
        }

        is_current_version = (
            not version.document.current_version_id
            or version.document.current_version_id == version.id
        )
        if is_current_version:
            version.document.document_type = classification
            version.document.label_tags = [tag for tag in tags if not tag.startswith("document_type:")]
            version.document.due_date = due_date
            # Keep the document-level JSON field store aligned with the
            # current version's extracted values. Dedicated columns remain
            # authoritative for document type and due date.
            document_data = dict(version.document.data or {})
            document_data.update(version.extraction or {})
            document_data["document_type"] = version.document.document_type
            document_data["due_date"] = due_date.isoformat() if due_date else None
            version.document.data = document_data
            if (version.document.workflow_notes or "").startswith("Processing failed:"):
                version.document.workflow_notes = None
        version.page_count = page_count

        if version.storage_size_bytes is None and file_bytes is not None:
            version.storage_size_bytes = len(file_bytes)

        # Every successfully processed upload must be reviewed, regardless
        # of OCR confidence. Keep this at the end of processing so failed
        # extraction does not leave a queue item that looks ready to review.
        # The unique-per-version queue row is preserved on reprocessing so
        # an existing review status is not reset to pending.
        existing_queue_item = (
            db.query(OCRCorrectionQueue)
            .filter(OCRCorrectionQueue.document_version_id == version.id)
            .one_or_none()
        )
        if not existing_queue_item:
            db.add(OCRCorrectionQueue(
                document_version_id=version.id,
                status=CorrectionStatus.pending,
            ))

            # Word-level evidence is retained for low-confidence OCR only;
            # high-confidence documents still get a correction queue row.
            word_boxes = (
                getattr(doctr_result, "word_boxes", None) or []
                if (version.ocr_meta or {}).get("low_confidence")
                else []
            )
            for wb in word_boxes:
                db.add(OCRWordBox(
                    document_version_id=version.id,
                    page=wb["page"],
                    bbox=wb["bbox"],
                    text_raw=wb["text"],
                    confidence=wb["confidence"],
                ))
            logger.info(
                "Pipeline stage=correction_queue_created version_id=%s low_confidence=%s word_count=%s",
                version.id,
                (version.ocr_meta or {}).get("low_confidence"),
                len(word_boxes),
            )

        version.processing_status = ProcessingStatus.uploaded
        logger.info(
            "Pipeline stage=assign_done version_id=%s status=%s tags=%s",
            version.id,
            version.processing_status.value,
            len(tags),
        )
        logger.info(
            "Document processed version_id=%s filename=%s status=%s doctr=%s doctr_vendor_tag=%s classification=%s confidence=%s tags=%s vendor_tag=%s",
            version.id,
            version.document.filename,
            version.processing_status.value,
            doctr_status,
            vendor_tag_from_doctr or "",
            (
                classification.value
                if hasattr(classification, "value")
                else classification
            ),
            confidence,
            len(tags),
            next((t for t in tags if t.startswith("vendor:")), ""),
        )

    except Exception as exc:
        version.processing_status = ProcessingStatus.failed
        # Flag WHY it failed, not just that it did. workflow_notes is
        # already surfaced in the existing WorkflowEditor UI, so this is
        # visible to a person looking at the document - not just a log
        # line nobody sees. Truncated: this is a note field, not a log.
        failure_note = f"Processing failed: {exc}"
        version.document.workflow_notes = failure_note[:2000]
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
