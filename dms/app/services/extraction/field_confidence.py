"""
app/services/extraction/field_confidence.py

Computes a per-field confidence score by fuzzy-matching each extracted
field's value against the document's stored OCRWordBox rows.

Why this exists: DocTR gives per-WORD confidence. Ollama's KIE step
returns flat field values (e.g. {"invoice_number": "INV-2025-00842"})
with no native link back to which OCR words produced that string - the
LLM just reads the full OCR text and outputs JSON. So "how confident are
we in the invoice_number field specifically" isn't something either
model tracks on its own; it has to be reconstructed here.

Approach: normalize the field's value and each word's text, find words
whose text appears as a substring match (case-insensitive, whitespace-
collapsed) within the field value, and take the MINIMUM confidence
among matched words (matching the zero-tolerance philosophy - one bad
word in a multi-word field value should surface as low confidence for
that field, not get averaged away).

Limitations, stated plainly:
  - Multi-word field values (e.g. a vendor address) match against
    multiple word boxes; single-token values (a date, an invoice
    number written as one token) match at most one.
  - If no word box matches at all (the LLM's value doesn't appear
    verbatim in the OCR text - e.g. it reformatted a date), the field
    gets no computed confidence and the UI should treat it as
    "unknown" rather than assuming either high or low confidence.
  - This is a heuristic, not a model output. It's good enough to drive
    the correction UI's per-field badges, not a substitute for the
    document-level ocr_low_confidence flag, which remains the source
    of truth for whether a document enters the queue at all.
"""
from __future__ import annotations

import re
from typing import Any


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def compute_field_confidences(
    fields: dict[str, Any],
    word_boxes: list[dict[str, Any]],
) -> dict[str, float | None]:
    """Returns {field_name: confidence or None} for each field in `fields`.

    `word_boxes` items are expected to have "text" and "confidence" keys
    (matches the OCRWordBox model's text_raw/confidence columns).
    """
    normalized_words = [
        (_normalize(str(wb.get("text_raw") or wb.get("text") or "")), wb["confidence"])
        for wb in word_boxes
        if (wb.get("text_raw") or wb.get("text"))
    ]

    result: dict[str, float | None] = {}
    for field_name, raw_value in fields.items():
        if raw_value is None:
            result[field_name] = None
            continue

        value_norm = _normalize(str(raw_value))
        if not value_norm:
            result[field_name] = None
            continue

        matched_confidences = [
            conf for word_norm, conf in normalized_words
            if word_norm and (word_norm in value_norm or value_norm in word_norm)
        ]

        result[field_name] = min(matched_confidences) if matched_confidences else None

    return result