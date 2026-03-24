from __future__ import annotations

import os
import re
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.db.models.enums import DocumentClass


TAG_PATTERNS: dict[str, tuple[str, ...]] = {
    "invoice": ("invoice", "bill", "po", "purchase order", "due date"),
    "payment": ("payment", "paid", "balance due", "amount due"),
    "receipt": ("receipt", "subtotal", "tax", "total"),
    "contract": ("contract", "agreement", "party", "term", "effective date"),
    "legal": ("clause", "liability", "indemn", "governing law", "jurisdiction"),
    "banking": ("account", "statement", "debit", "credit", "transaction"),
    "identity": ("name", "address", "phone", "email"),
}

SENSITIVE_PATTERNS: tuple[str, ...] = (
    "social security",
    "ssn",
    "salary",
    "payroll",
    "confidential",
    "bank account",
)

CLASSIFICATION_TO_DOC_TYPE: dict[str, str] = {
    "incoming_invoice": "incoming_invoice",
    "outgoing_invoice": "outgoing_invoice",
    "invoice": "invoice",
    "receipt": "receipt",
    "contract": "contract",
    "unknown": "document",
}

RESERVED_TAG_PREFIXES = (
    "project:",
    "document_type:",
    "security_clearance:",
    "company:",
)


@lru_cache(maxsize=1)
def _load_tagger_model() -> dict[str, Any] | None:
    path = os.getenv("TAGGER_MODEL_PATH", "").strip()
    if not path:
        return None
    try:
        import joblib
    except Exception:
        return None
    return joblib.load(path)


def _as_string(value: str | Enum | None) -> str | None:
    """Handle as string.

    Parameters:
        value (type=str | Enum | None): Function argument used by this operation.
    """
    if value is None:
        return None
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def _derive_project_tag(text: str, filename: str | None) -> str:
    """Handle derive project tag.

    Parameters:
        text (type=str): Function argument used by this operation.
        filename (type=str | None): File or entity name used for storage and display.
    """
    patterns = (
        r"\bproject[\s:#-]+([A-Za-z0-9][A-Za-z0-9_-]{1,63})\b",
        r"\bproj[\s:#-]+([A-Za-z0-9][A-Za-z0-9_-]{1,63})\b",
    )
    lowered = text.lower()
    for pattern in patterns:
        match = re.search(pattern, lowered)
        if match:
            return f"project:{match.group(1)}"

    if filename:
        # Accept explicit file naming conventions like project_acme_invoice.pdf
        base = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].lower()
        match = re.search(
            r"(?:^|[_\-.])project[_\-.]?([a-z0-9][a-z0-9_-]{1,63})(?:[_\-.]|$)",
            base,
        )
        if match:
            return f"project:{match.group(1)}"

    return "project:unassigned"


def _derive_company_tag(
    text: str,
    filename: str | None,
    existing_tags: list[str] | None,
) -> str:
    """Handle derive company tag.

    Parameters:
        text (type=str): Function argument used by this operation.
        filename (type=str | None): File or entity name used for storage and display.
        existing_tags (type=list[str] | None): Known tag catalog used for matching.
    """
    lowered = text.lower()

    if existing_tags:
        normalized_text = re.sub(r"[^a-z0-9]+", " ", lowered)
        words = set(normalized_text.split())
        for raw in existing_tags:
            candidate = normalize_tag(raw)
            if not candidate or not candidate.startswith("company:"):
                continue
            base = candidate.split(":", 1)[1]
            phrase = re.sub(r"[_-]+", " ", base).strip()
            if len(phrase) >= 3 and phrase in normalized_text:
                return candidate
            parts = [p for p in phrase.split() if len(p) >= 3]
            if parts and all(part in words for part in parts):
                return candidate

    patterns = (
        r"\bcompany[\s:#-]+([A-Za-z0-9][A-Za-z0-9_.-]{1,63})\b",
        r"\bvendor[\s:#-]+([A-Za-z0-9][A-Za-z0-9_.-]{1,63})\b",
        r"\bcustomer[\s:#-]+([A-Za-z0-9][A-Za-z0-9_.-]{1,63})\b",
    )
    for pattern in patterns:
        match = re.search(pattern, lowered)
        if match:
            return f"company:{match.group(1)}"

    if filename:
        # Accept explicit file naming conventions like company_acme_invoice.pdf
        base = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].lower()
        match = re.search(
            r"(?:^|[_\-.])company[_\-.]?([a-z0-9][a-z0-9_.-]{1,63})(?:[_\-.]|$)",
            base,
        )
        if match:
            return f"company:{match.group(1)}"

    return ""


def _derive_document_type_tag(
    document_type: str | Enum | None,
    classification: DocumentClass | str | None,
) -> str:
    """Handle derive document type tag.

    Parameters:
        document_type (type=str | Enum | None): Function argument used by this operation.
        classification (type=DocumentClass | str | None): Function argument used by this operation.
    """
    explicit = _as_string(document_type)
    if explicit:
        return f"document_type:{explicit}"

    inferred = _as_string(classification)
    if inferred:
        return f"document_type:{CLASSIFICATION_TO_DOC_TYPE.get(inferred, inferred)}"

    return "document_type:document"


def _derive_security_clearance_tag(
    text: str,
    document_type: str | Enum | None,
    classification: DocumentClass | str | None,
) -> str:
    """Handle derive security clearance tag.

    Parameters:
        text (type=str): Function argument used by this operation.
        document_type (type=str | Enum | None): Function argument used by this operation.
        classification (type=DocumentClass | str | None): Function argument used by this operation.
    """
    lowered = text.lower()
    doc_type = (_as_string(document_type) or "").lower()
    doc_class = (_as_string(classification) or "").lower()

    if any(pattern in lowered for pattern in SENSITIVE_PATTERNS) or doc_type == "payroll":
        return "security_clearance:admin"

    if doc_type in {"contract", "manual"} or doc_class == "contract":
        return "security_clearance:editor"

    return "security_clearance:viewer"


def normalize_tag(raw_tag: str) -> str:
    """Handle normalize tag.

    Parameters:
        raw_tag (type=str): Function argument used by this operation.
    """
    tag = re.sub(r"\s+", " ", (raw_tag or "").strip().lower())
    if not tag:
        return ""
    # Keep values stable and machine-friendly.
    tag = tag.replace(" ", "_")
    tag = re.sub(r"[^a-z0-9:_-]", "", tag)
    return tag


def _suggest_existing_tags(
    context_text: str,
    existing_tags: list[str] | None,
) -> set[str]:
    """Handle suggest existing tags.

    Parameters:
        context_text (type=str): Function argument used by this operation.
        existing_tags (type=list[str] | None): Function argument used by this operation.
    """
    if not existing_tags:
        return set()

    normalized_text = re.sub(r"[^a-z0-9]+", " ", context_text.lower())
    words = set(normalized_text.split())
    suggested: set[str] = set()

    for raw in existing_tags:
        candidate = normalize_tag(raw)
        if not candidate:
            continue
        # Keep mandatory families deterministic from current derivation logic.
        if candidate.startswith(RESERVED_TAG_PREFIXES):
            continue

        base = candidate.split(":", 1)[1] if ":" in candidate else candidate
        phrase = re.sub(r"[_-]+", " ", base).strip()
        if len(phrase) >= 3 and phrase in normalized_text:
            suggested.add(candidate)
            continue

        parts = [p for p in phrase.split() if len(p) >= 3]
        if parts and all(part in words for part in parts):
            suggested.add(candidate)

    return suggested


def _predict_model_tags(text: str) -> set[str]:
    model_bundle = _load_tagger_model()
    if not model_bundle:
        return set()
    vectorizer = model_bundle.get("vectorizer")
    model = model_bundle.get("model")
    labels = model_bundle.get("labels") or []
    if vectorizer is None or model is None or not labels:
        return set()
    features = vectorizer.transform([text or ""])
    threshold = float(os.getenv("TAGGER_THRESHOLD", "0.5"))
    predicted: set[str] = set()
    if hasattr(model, "predict_proba"):
        probs = model.predict_proba(features)
        if isinstance(probs, list):
            probs = probs[0]
        for label, prob in zip(labels, probs):
            if prob >= threshold:
                predicted.add(str(label))
    else:
        outputs = model.predict(features)
        if outputs is not None and len(outputs):
            row = outputs[0]
            for label, value in zip(labels, row):
                if value:
                    predicted.add(str(label))
    return predicted


def derive_tags(
    text: str,
    classification: DocumentClass | str | None,
    *,
    document_type: str | Enum | None = None,
    filename: str | None = None,
    existing_tags: list[str] | None = None,
) -> list[str]:
    """Derive deterministic tags from extracted text and classification.

    Parameters:
        text (type=str): Function argument used by this operation.
        classification (type=DocumentClass | str | None): Function argument used by this operation.
        document_type (type=str | Enum | None, default=None): Function argument used by this operation.
        filename (type=str | None, default=None): File or entity name used for storage and display.
        existing_tags (type=list[str] | None, default=None): Function argument used by this operation.
    """
    tags: set[str] = set()
    normalized = (text or "").lower()
    filename_base = Path(filename or "").name.lower()

    # Mandatory tags on every document.
    tags.add(normalize_tag(_derive_project_tag(normalized, filename)))
    company_tag = normalize_tag(_derive_company_tag(normalized, filename, existing_tags))
    if company_tag:
        tags.add(company_tag)
    tags.add(normalize_tag(_derive_document_type_tag(document_type, classification)))
    tags.add(
        normalize_tag(
            _derive_security_clearance_tag(normalized, document_type, classification)
        )
    )

    if classification:
        tags.add(normalize_tag(str(classification).split(".")[-1].lower()))

    for tag, patterns in TAG_PATTERNS.items():
        for pattern in patterns:
            if re.search(rf"\b{re.escape(pattern)}\b", normalized):
                tags.add(normalize_tag(tag))
                break

    context = f"{normalized} {filename_base} {_as_string(classification) or ''} {_as_string(document_type) or ''}"
    tags.update(_suggest_existing_tags(context, existing_tags))
    tags.update(_predict_model_tags(context))

    # Avoid low-quality fallback if a specific project was found.
    if "project:unassigned" in tags and any(
        tag.startswith("project:") and tag != "project:unassigned" for tag in tags
    ):
        tags.discard("project:unassigned")

    return sorted(tags)
