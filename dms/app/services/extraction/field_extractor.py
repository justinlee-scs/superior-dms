from __future__ import annotations

import io
import os
import re
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image

from app.services.extraction.opencv_preprocess import preprocess_pil_image
from app.services.extraction.pdf import pdf_to_images
from app.services.extraction.tags import normalize_tag


@dataclass(frozen=True)
class OCRToken:
    text: str
    x: float
    y: float
    w: float
    h: float
    x_abs: float
    y_abs: float
    w_abs: float
    h_abs: float
    page: int


FIELD_TAG_MAP: dict[str, str] = {
    "Vendor": "company",
    "Document Date": "document_date",
    "Payment Due Date": "due_date",
    "Pre-Tax Line Total": "pretax_total",
    "Post-Tax Line Total": "posttax_total",
    "Grand Total": "grand_total",
    "Unit Price": "unit_price",
    "Sales Tax Code": "sales_tax_code",
    "Bill To": "bill_to",
    "Ship To": "ship_to",
    "PO #": "po_number",
    "Account/Client #": "account_number",
    "Invoice #": "invoice_number",
    "Delivery/Service Date (for fuel esp)": "service_date",
    "Docket/Packing Slip #": "docket_number",
    "Product/Service Description": "item_description",
    "Quantity": "quantity",
    "Equipment #": "equipment_number",
    "Document Type": "document_type",
    "Subtotal": "subtotal",
    "GST #": "gst_number",
    "PST #": "pst_number",
    "Store #": "store_number",
    "Signature": "signature",
    "Discount": "discount",
    "Payment Terms (eg. Net 30, Due on Receipt)": "payment_terms",
    "Bank/Payment Details": "bank_details",
    "Parties Involved": "parties",
    "Subject Line": "subject",
}


def _clean_value(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def _snake(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    return cleaned or "field"


def _parse_date(value: str) -> date | None:
    text = value.strip()
    match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            return None
    match = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b", text)
    if match:
        month = int(match.group(1))
        day = int(match.group(2))
        year = int(match.group(3))
        if year < 100:
            year += 2000
        try:
            return date(year, month, day)
        except ValueError:
            return None
    match = re.search(r"\b(\d{1,2})-(\d{1,2})-(\d{2,4})\b", text)
    if match:
        month = int(match.group(1))
        day = int(match.group(2))
        year = int(match.group(3))
        if year < 100:
            year += 2000
        try:
            return date(year, month, day)
        except ValueError:
            return None
    return None


def fields_to_tags(fields: dict[str, str]) -> list[str]:
    tags: list[str] = []
    for field, raw_value in fields.items():
        value = _clean_value(raw_value)
        if not value:
            continue
        prefix = FIELD_TAG_MAP.get(field) or _snake(field)
        if prefix in {"due_date", "document_date", "service_date"}:
            parsed = _parse_date(value)
            if not parsed:
                continue
            tag = f"{prefix}:{parsed.isoformat()}"
        else:
            tag = f"{prefix}:{value}"
        normalized = normalize_tag(tag)
        if normalized:
            tags.append(normalized)
    return tags


@lru_cache(maxsize=1)
def _load_model() -> dict[str, object] | None:
    path = os.getenv("FIELD_EXTRACTOR_MODEL_PATH", "").strip()
    if not path:
        return None
    try:
        import joblib
    except Exception:
        return None
    if not Path(path).exists():
        return None
    return joblib.load(path)


def clear_field_extractor_cache() -> None:
    _load_model.cache_clear()


def _tokenize_image(image: Image.Image, page: int) -> list[OCRToken]:
    try:
        from pytesseract import Output
        import pytesseract
    except Exception:
        return []

    try:
        processed = preprocess_pil_image(image)
    except Exception:
        processed = image

    data = pytesseract.image_to_data(processed, output_type=Output.DICT)
    tokens: list[OCRToken] = []
    width, height = processed.size
    for i, text in enumerate(data.get("text", [])):
        if not text or not str(text).strip():
            continue
        try:
            conf = float(data.get("conf", [0])[i])
        except Exception:
            conf = 0.0
        if conf < 0:
            continue
        x = float(data.get("left", [0])[i])
        y = float(data.get("top", [0])[i])
        w = float(data.get("width", [0])[i])
        h = float(data.get("height", [0])[i])
        tokens.append(
            OCRToken(
                text=str(text).strip(),
                x=x / width if width else 0.0,
                y=y / height if height else 0.0,
                w=w / width if width else 0.0,
                h=h / height if height else 0.0,
                x_abs=x,
                y_abs=y,
                w_abs=w,
                h_abs=h,
                page=page,
            )
        )
    return tokens


def _load_images(file_bytes: bytes, filename: str) -> list[Image.Image]:
    suffix = Path(filename or "").suffix.lower()
    if suffix == ".pdf":
        return pdf_to_images(file_bytes)
    return [Image.open(io.BytesIO(file_bytes)).convert("RGB")]


def extract_fields(file_bytes: bytes, filename: str) -> dict[str, str]:
    bundle = _load_model()
    if not bundle:
        return {}

    vectorizer = bundle.get("vectorizer")
    scaler = bundle.get("scaler")
    model = bundle.get("model")
    if vectorizer is None or scaler is None or model is None:
        return {}

    tokens: list[OCRToken] = []
    images = _load_images(file_bytes, filename)
    for idx, img in enumerate(images, start=1):
        tokens.extend(_tokenize_image(img, idx))

    if not tokens:
        return {}

    import scipy.sparse

    texts = [t.text for t in tokens]
    numeric = np.array([[t.x, t.y, t.w, t.h, float(t.page)] for t in tokens], dtype=float)
    text_vec = vectorizer.transform(texts)
    num_vec = scaler.transform(numeric)
    features = scipy.sparse.hstack([text_vec, num_vec])
    probs = model.predict_proba(features)
    labels = model.classes_

    min_conf = float(os.getenv("FIELD_EXTRACTOR_MIN_CONFIDENCE", "0.45"))
    selections: dict[str, list[tuple[OCRToken, float]]] = {}
    for token, row in zip(tokens, probs):
        best_idx = int(np.argmax(row))
        label = str(labels[best_idx])
        confidence = float(row[best_idx])
        if label == "O" or confidence < min_conf:
            continue
        selections.setdefault(label, []).append((token, confidence))

    fields: dict[str, str] = {}
    for label, items in selections.items():
        items.sort(key=lambda item: (item[0].page, item[0].y, item[0].x))
        text = " ".join(tok.text for tok, _ in items).strip()
        if text:
            fields[label] = text
    return fields


def predict_field_tokens(file_bytes: bytes, filename: str) -> list[dict[str, object]]:
    """Return token-level predictions for Label Studio previews."""
    bundle = _load_model()
    if not bundle:
        return []

    vectorizer = bundle.get("vectorizer")
    scaler = bundle.get("scaler")
    model = bundle.get("model")
    if vectorizer is None or scaler is None or model is None:
        return []

    tokens: list[OCRToken] = []
    images = _load_images(file_bytes, filename)
    for idx, img in enumerate(images, start=1):
        tokens.extend(_tokenize_image(img, idx))

    if not tokens:
        return []

    import scipy.sparse

    texts = [t.text for t in tokens]
    numeric = np.array([[t.x, t.y, t.w, t.h, float(t.page)] for t in tokens], dtype=float)
    text_vec = vectorizer.transform(texts)
    num_vec = scaler.transform(numeric)
    features = scipy.sparse.hstack([text_vec, num_vec])
    probs = model.predict_proba(features)
    labels = model.classes_

    min_conf = float(os.getenv("FIELD_EXTRACTOR_MIN_CONFIDENCE", "0.45"))
    predictions: list[dict[str, object]] = []
    for token, row in zip(tokens, probs):
        best_idx = int(np.argmax(row))
        label = str(labels[best_idx])
        confidence = float(row[best_idx])
        if label == "O" or confidence < min_conf:
            continue
        predictions.append(
            {
                "label": label,
                "text": token.text,
                "confidence": confidence,
                "x": token.x,
                "y": token.y,
                "w": token.w,
                "h": token.h,
                "x_abs": token.x_abs,
                "y_abs": token.y_abs,
                "w_abs": token.w_abs,
                "h_abs": token.h_abs,
                "page": token.page,
            }
        )
    return predictions
