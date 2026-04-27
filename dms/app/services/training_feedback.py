from __future__ import annotations

from enum import Enum
from typing import Iterable
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models.training_feedback_event import TrainingFeedbackEvent


def _enum_str(value: str | Enum | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def _normalized_tags(tags: Iterable[str] | None) -> list[str]:
    if not tags:
        return []
    values = {str(tag).strip().lower() for tag in tags if str(tag).strip()}
    return sorted(values)


def capture_feedback_event(
    db: Session,
    *,
    document_id: UUID,
    document_version_id: UUID | None,
    edited_by_user_id: UUID | None,
    event_type: str,
    predicted_tags: Iterable[str] | None,
    final_tags: Iterable[str] | None,
    predicted_document_type: str | Enum | None,
    final_document_type: str | Enum | None,
    extracted_text_snapshot: str | None,
    model_confidence: float | None,
    model_version: str | None,
    source: str = "dms_ui",
    include_in_training: bool = True,
) -> TrainingFeedbackEvent:
    event = TrainingFeedbackEvent(
        document_id=document_id,
        document_version_id=document_version_id,
        edited_by_user_id=edited_by_user_id,
        source=source,
        event_type=event_type,
        predicted_tags=_normalized_tags(predicted_tags),
        final_tags=_normalized_tags(final_tags),
        predicted_document_type=_enum_str(predicted_document_type),
        final_document_type=_enum_str(final_document_type),
        extracted_text_snapshot=(extracted_text_snapshot or "").strip() or None,
        model_confidence=model_confidence,
        model_version=(model_version or "").strip() or None,
        include_in_training=include_in_training,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
