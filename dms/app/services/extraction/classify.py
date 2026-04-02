from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from app.db.models.enums import DocumentClass


@lru_cache(maxsize=1)
def _load_model() -> dict[str, Any] | None:
    path = os.getenv("DOC_CLASS_MODEL_PATH", "").strip()
    if not path:
        return None
    try:
        import joblib
    except Exception:
        return None
    return joblib.load(path)


def classify_document(text: str) -> DocumentClass:
    """Very simple heuristic classifier.

    Parameters:
        text (type=str): Function argument used by this operation.
    """

    model_bundle = _load_model()
    if model_bundle:
        vectorizer = model_bundle.get("vectorizer")
        model = model_bundle.get("model")
        labels = model_bundle.get("labels")
        if vectorizer is not None and model is not None and labels:
            features = vectorizer.transform([text or ""])
            prediction = model.predict(features)[0]
            try:
                return DocumentClass(prediction)
            except Exception:
                pass

    lowered = (text or "").lower()

    if "invoice" in lowered:
        incoming_signals = (
            "vendor",
            "supplier",
            "remit to",
            "pay to",
            "amount due",
        )
        outgoing_signals = (
            "bill to",
            "invoice to",
            "customer",
            "ship to",
            "sold to",
        )
        has_incoming = any(signal in lowered for signal in incoming_signals)
        has_outgoing = any(signal in lowered for signal in outgoing_signals)
        if has_incoming and not has_outgoing:
            return DocumentClass.INCOMING_INVOICE
        if has_outgoing and not has_incoming:
            return DocumentClass.OUTGOING_INVOICE
        return DocumentClass.INVOICE

    if "receipt" in lowered:
        return DocumentClass.RECEIPT

    if "agreement" in lowered or "contract" in lowered:
        return DocumentClass.CONTRACT

    return DocumentClass.UNKNOWN


def classify_document_with_score(text: str) -> tuple[DocumentClass, float]:
    """Return classification plus confidence score when model supports it."""
    model_bundle = _load_model()
    if model_bundle:
        vectorizer = model_bundle.get("vectorizer")
        model = model_bundle.get("model")
        labels = model_bundle.get("labels")
        if vectorizer is not None and model is not None and labels:
            features = vectorizer.transform([text or ""])
            if hasattr(model, "predict_proba"):
                probs = model.predict_proba(features)[0]
                best_idx = int(probs.argmax())
                best_label = labels[best_idx]
                try:
                    return DocumentClass(best_label), float(probs[best_idx])
                except Exception:
                    return DocumentClass.UNKNOWN, float(probs[best_idx])
            prediction = model.predict(features)[0]
            try:
                return DocumentClass(prediction), 0.0
            except Exception:
                return DocumentClass.UNKNOWN, 0.0

    return classify_document(text), 0.0


def clear_classifier_cache() -> None:
    _load_model.cache_clear()
