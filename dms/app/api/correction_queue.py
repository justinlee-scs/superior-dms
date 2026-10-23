"""
app/api/correction_queue.py

FastAPI router for the DocTR correction queue - field-value form only,
no bounding-box UI (decided: correction UI is a simple field-value form).

"""
from __future__ import annotations

import logging
import json
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.document_versions import DocumentVersion
from app.db.models.ocr_correction import OCRCorrectionQueue, OCRWordBox, ExtractionFieldCorrection
from app.db.models.documents import Document
from app.db.models.tag_catalog import TagCatalog
from app.db.models.user import User
from app.auth.deps import get_current_user  # adjust if the real dependency lives elsewhere
from app.services.extraction.field_confidence import compute_field_confidences
from app.services.training_feedback import capture_feedback_event
from app.services.extraction.due_dates import parse_date_value
from app.services.extraction.field_extractor import normalize_extracted_fields
from app.services.extraction.tags import normalize_tag

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/correction-queue", tags=["correction-queue"])

# Same threshold doctr_engine.py flags on - a field is "low confidence"
# if its matched word confidence falls below this, or if no word could
# be matched to it at all (treated as needing review, not assumed fine).
FIELD_CONFIDENCE_THRESHOLD = 0.70


# --------------------------------------------------------------------------
# Schemas
# --------------------------------------------------------------------------

class QueueItemOut(BaseModel):
    id: str
    document_version_id: str
    status: str
    created_at: datetime
    low_confidence_field_count: int
    total_field_count: int
    filename: str
    document_type: Optional[str]

    class Config:
        from_attributes = True


class FieldOut(BaseModel):
    field_name: str
    value: Any
    confidence: Optional[float]  # None = no matching word found, treat as needs-review
    low_confidence: bool


class DocumentDetailOut(BaseModel):
    document_version_id: str
    status: str
    fields: list[FieldOut]
    document_types: list[str]
    document_data: dict[str, Any]


class FieldResolution(BaseModel):
    field_name: str
    value_corrected: Any
    # "accepted" = value unchanged, user confirmed it's correct
    # "corrected" = user changed the value
    # "rejected" = field doesn't apply / should be cleared
    action: Literal["accepted", "corrected", "rejected"]


class SubmitCorrectionIn(BaseModel):
    fields: list[FieldResolution]


def _correction_text(value) -> Optional[str]:
    """Store correction history values in the table text columns safely."""
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------

@router.get("", response_model=list[QueueItemOut])
def list_queue(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(OCRCorrectionQueue)
    if status:
        stmt = stmt.where(OCRCorrectionQueue.status == status)
    else:
        stmt = stmt.where(OCRCorrectionQueue.status != "confirmed")
    items = db.execute(stmt.order_by(OCRCorrectionQueue.created_at)).scalars().all()

    out = []
    for item in items:
        dv = db.get(DocumentVersion, item.document_version_id)
        fields = dv.extraction or {} if dv else {}
        boxes = db.execute(
            select(OCRWordBox).where(OCRWordBox.document_version_id == item.document_version_id)
        ).scalars().all()
        word_dicts = [{"text_raw": b.text_raw, "confidence": b.confidence} for b in boxes]
        field_confidences = compute_field_confidences(fields, word_dicts)
        low_conf_count = sum(
            1 for c in field_confidences.values()
            if c is None or c < FIELD_CONFIDENCE_THRESHOLD
        )
        out.append(QueueItemOut(
            id=str(item.id),
            document_version_id=str(item.document_version_id),
            status=item.status,
            created_at=item.created_at,
            low_confidence_field_count=low_conf_count,
            total_field_count=len(fields),
            filename=dv.document.filename if dv and dv.document else "unknown",
            document_type=(
                dv.document.document_type
                if dv and dv.document and dv.document.document_type
                else None
            ),
        ))
    return out


@router.get("/{document_version_id}", response_model=DocumentDetailOut)
def get_document_for_review(
    document_version_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dv = db.get(DocumentVersion, document_version_id)
    if not dv:
        raise HTTPException(404, "Document version not found")

    queue_item = db.execute(
        select(OCRCorrectionQueue).where(OCRCorrectionQueue.document_version_id == document_version_id)
    ).scalar_one_or_none()
    if not queue_item:
        raise HTTPException(404, "Not in correction queue")

    if queue_item.status == "pending":
        queue_item.status = "in_review"
        db.commit()

    fields = normalize_extracted_fields(dv.extraction)
    # The document row is canonical for type. If extraction did not return
    # a type or due date, show the value the app actually stores rather than
    # a blank that could accidentally erase existing canonical data.
    if fields.get("document_type") is None and dv.document and dv.document.document_type:
        fields["document_type"] = dv.document.document_type
    if fields.get("due_date") is None and dv.document and dv.document.due_date:
        fields["due_date"] = dv.document.due_date.isoformat()
    boxes = db.execute(
        select(OCRWordBox).where(OCRWordBox.document_version_id == document_version_id)
    ).scalars().all()
    word_dicts = [{"text_raw": b.text_raw, "confidence": b.confidence} for b in boxes]
    field_confidences = compute_field_confidences(fields, word_dicts)

    field_list = [
        FieldOut(
            field_name=name,
            value=value,
            confidence=field_confidences.get(name),
            low_confidence=(
                field_confidences.get(name) is None
                or field_confidences.get(name) < FIELD_CONFIDENCE_THRESHOLD
            ),
        )
        for name, value in fields.items()
    ]

    return DocumentDetailOut(
        document_version_id=str(document_version_id),
        status=queue_item.status,
        fields=field_list,
        document_types=[
            tag.name
            for tag in db.query(TagCatalog)
            .filter(TagCatalog.kind == "document_type")
            .order_by(TagCatalog.name.asc())
            .all()
        ],
        document_data=normalize_extracted_fields(dv.document.data) if dv.document else {},
    )


@router.post("/{document_version_id}/submit")
def submit_correction(
    document_version_id: str,
    payload: SubmitCorrectionIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dv = db.get(DocumentVersion, document_version_id)
    if not dv:
        raise HTTPException(404, "Document version not found")

    queue_item = db.execute(
        select(OCRCorrectionQueue).where(OCRCorrectionQueue.document_version_id == document_version_id)
    ).scalar_one_or_none()
    if not queue_item:
        raise HTTPException(404, "Not in correction queue")

    original_fields = normalize_extracted_fields(dv.extraction)
    if original_fields.get("document_type") is None and dv.document and dv.document.document_type:
        original_fields["document_type"] = dv.document.document_type
    if original_fields.get("due_date") is None and dv.document and dv.document.due_date:
        original_fields["due_date"] = dv.document.due_date.isoformat()

    # --- Hard gate: EVERY field must have a resolution. Zero tolerance
    #     means no partial saves - matches "0 of N fields resolved"
    #     tracking in the UI. A field counts as resolved once it has
    #     any entry here, whether accepted as-is or corrected. ---
    vendor_aliases = {"company", "company_name", "vendor_name", "supplier", "supplier_name"}
    def canonical_field_name(name: str) -> str:
        normalized_name = name.strip().lower().replace(" ", "_")
        return "vendor" if normalized_name in vendor_aliases else name

    resolved_names = {
        canonical_field_name(field.field_name)
        for field in payload.fields
    }
    missing = set(original_fields.keys()) - resolved_names
    if missing:
        raise HTTPException(
            400,
            f"{len(missing)} field(s) not resolved: {sorted(missing)} - "
            f"every extracted field must be accepted, corrected, or rejected before submit.",
        )

    corrected_fields = dict(original_fields)
    for fr in payload.fields:
        field_name = canonical_field_name(fr.field_name)
        raw_value = original_fields.get(field_name)
        db.add(ExtractionFieldCorrection(
            document_version_id=document_version_id,
            field_name=field_name,
            value_raw=_correction_text(raw_value),
            value_corrected=_correction_text(fr.value_corrected),
        ))
        if fr.action == "rejected":
            corrected_fields[field_name] = None
        elif fr.action == "accepted":
            # The UI sends a display string for every value. Preserve the
            # original JSON structure when the user confirms it unchanged.
            corrected_fields[field_name] = raw_value
        else:
            corrected_fields[field_name] = fr.value_corrected

    document = dv.document
    updates_document = bool(
        document
        and (
            document.current_version_id is None
            or document.current_version_id == dv.id
        )
    )
    if document and updates_document:
        # documents.data is the queryable, canonical field snapshot for the
        # active version. Keep it in sync with the corrected version JSON.
        document_data = normalize_extracted_fields(document.data)
        document_data.update(corrected_fields)

        if "document_type" in corrected_fields:
            type_value = corrected_fields["document_type"]
            if type_value is None or (isinstance(type_value, str) and not type_value.strip()):
                document.document_type_tag = None
                document_data["document_type"] = None
            elif not isinstance(type_value, str):
                raise HTTPException(422, "Document type must be a type name")
            else:
                normalized_type = normalize_tag(type_value)
                type_tag = db.query(TagCatalog).filter_by(
                    name=normalized_type, kind="document_type"
                ).one_or_none()
                if type_tag is None:
                    raise HTTPException(
                        422,
                        f"Unknown document type '{type_value}'. Choose a type from the available list.",
                    )
                document.document_type_tag = type_tag
                document_data["document_type"] = type_tag.name

        if "due_date" in corrected_fields:
            due_date_value = corrected_fields["due_date"]
            parsed_due_date = parse_date_value(due_date_value)
            if due_date_value not in (None, "") and parsed_due_date is None:
                raise HTTPException(422, "Due date must be a valid calendar date")
            document.due_date = parsed_due_date
            document_data["due_date"] = parsed_due_date.isoformat() if parsed_due_date else None

        # Keep the namespaced labels shown by the document list aligned with
        # corrected issuer fields. These are labels; document type and due
        # date remain their dedicated canonical columns.
        labels = set(document.label_tags or [])
        if "vendor" in corrected_fields:
            labels = {
                label for label in labels
                if not label.startswith(("company:", "vendor:"))
            }
            vendor_value = corrected_fields.get("vendor")
            vendor_tag = normalize_tag(f"vendor:{vendor_value}") if isinstance(vendor_value, str) and vendor_value.strip() else None
            if vendor_tag:
                labels.add(vendor_tag)
            document.label_tags = sorted(labels)

        document.data = document_data

    dv.extraction = corrected_fields
    queue_item.status = "confirmed"
    queue_item.confirmed_at = datetime.now(timezone.utc)
    queue_item.confirmed_by = user.id

    db.commit()

    # --- Feed the EXISTING nightly-retrain gate. TrainingFeedbackEvent is
    #     tag/classification-centric - this call just registers "a
    #     correction happened" for the threshold check in
    #     nightly_retrainer.py. The training payload itself comes from
    #     extraction_field_corrections, already committed above.
    try:
        capture_feedback_event(
            db,
            document_id=dv.document_id,
            document_version_id=dv.id,
            edited_by_user_id=user.id,
            event_type="ocr_field_correction",
            predicted_tags=None,
            final_tags=None,
            predicted_document_type=None,
            final_document_type=None,
            extracted_text_snapshot=dv.extracted_text,
            model_confidence=(dv.ocr_meta or {}).get("confidence_average"),
            model_version=(dv.ocr_meta or {}).get("model_version"),
            source="correction_queue",
            include_in_training=True,
        )
    except Exception:
        logger.warning(
            "Feedback event capture failed for version %s - correction saved, "
            "but this correction won't count toward the nightly retrain threshold.",
            document_version_id,
        )

    return {
        "status": "confirmed",
        "document_version_id": document_version_id,
        "document_updated": updates_document,
        "document_type": document.document_type if document else None,
        "due_date": document.due_date.isoformat() if document and document.due_date else None,
        "tags": document.label_tags if document else [],
        "document_data": document.data if document else {},
        "extraction": corrected_fields,
    }
