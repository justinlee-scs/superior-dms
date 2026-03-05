from __future__ import annotations

import re
from enum import Enum
from pathlib import Path

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
    "invoice": "incoming_invoice",
    "receipt": "receipt",
    "contract": "contract",
    "unknown": "document",
}

RESERVED_TAG_PREFIXES = (
    "project:",
    "document_type:",
    "security_clearance:",
)


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

    # Avoid low-quality fallback if a specific project was found.
    if "project:unassigned" in tags and any(
        tag.startswith("project:") and tag != "project:unassigned" for tag in tags
    ):
        tags.discard("project:unassigned")

    return sorted(tags)
