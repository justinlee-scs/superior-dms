import io
import os
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional, List
from pathlib import Path

from PIL import Image
import torch
from transformers import LayoutLMv3Processor, LayoutLMv3ForTokenClassification
from app.services.extraction.pdf import pdf_to_images


# ---- DATA STRUCTURE ----


@dataclass
class LiLTResult:
    text: str
    confidence: Optional[float]
    fields: Dict[str, Any]


# ---- CONFIG ----
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
logger = logging.getLogger(__name__)


# ---- MODEL LOAD ----

_PROCESSOR = None
_MODEL = None
_ID2LABEL = None
_MODEL_LOAD_FAILED_REASON = None


def clear_lilt_cache() -> None:
    global _PROCESSOR, _MODEL, _ID2LABEL
    _PROCESSOR = None
    _MODEL = None
    _ID2LABEL = None


def _get_model_name() -> str:
    model_name = os.getenv("LILT_MODEL_NAME", "").strip()
    if not model_name:
        raise RuntimeError(
            "LiLT is not configured: set LILT_MODEL_NAME to your Hugging Face model repo id"
        )
    return model_name


def _hf_auth_kwargs() -> dict[str, str]:
    token = (
        os.getenv("HUGGINGFACE_HUB_TOKEN", "").strip()
        or os.getenv("HF_TOKEN", "").strip()
    )
    return {"token": token} if token else {}


def _load_model():
    global _PROCESSOR, _MODEL, _ID2LABEL, _MODEL_LOAD_FAILED_REASON

    if _MODEL_LOAD_FAILED_REASON:
        raise RuntimeError(_MODEL_LOAD_FAILED_REASON)

    if _PROCESSOR is None or _MODEL is None:
        model_name = _get_model_name()
        auth_kwargs = _hf_auth_kwargs()
        try:
            _PROCESSOR = LayoutLMv3Processor.from_pretrained(
                model_name,
                apply_ocr=True,
                **auth_kwargs,
            )

            _MODEL = LayoutLMv3ForTokenClassification.from_pretrained(
                model_name,
                **auth_kwargs,
            )
            _MODEL.to(DEVICE)
            _MODEL.eval()

            _ID2LABEL = _MODEL.config.id2label
            logger.info("LiLT model loaded model=%s device=%s", model_name, DEVICE)
        except Exception as exc:
            _MODEL_LOAD_FAILED_REASON = f"LiLT unavailable for {model_name}: {exc}"
            logger.error(_MODEL_LOAD_FAILED_REASON)
            raise RuntimeError(_MODEL_LOAD_FAILED_REASON) from exc

    return _PROCESSOR, _MODEL, _ID2LABEL


# ---- TOKEN GROUPING (CRITICAL PART) ----


def _group_entities(tokens: List[str], labels: List[str]) -> Dict[str, str]:
    """
    Converts BIO-tagged tokens into structured fields
    Example labels:
        B-VENDOR, I-VENDOR
        B-INVOICE_NUMBER, I-INVOICE_NUMBER
        B-DUE_DATE, I-DUE_DATE
    """
    fields: Dict[str, List[str]] = {}

    current_field = None

    for token, label in zip(tokens, labels):
        if token in ("[CLS]", "[SEP]", "[PAD]"):
            continue

        if label.startswith("B-"):
            current_field = label[2:]
            fields.setdefault(current_field, []).append(token)

        elif label.startswith("I-") and current_field == label[2:]:
            fields[current_field].append(token)

        else:
            current_field = None

    # join tokens
    return {key.lower(): _clean_tokens(value) for key, value in fields.items()}


def _clean_tokens(tokens: List[str]) -> str:
    words = []
    for token in tokens:
        if token.startswith("##"):
            if words:
                words[-1] += token[2:]
        else:
            words.append(token)
    return " ".join(words)


# ---- MAIN FUNCTION ----


def run_lilt_model(
    *,
    file_bytes: bytes,
    filename: str,
) -> LiLTResult:
    processor, model, id2label = _load_model()

    suffix = Path(filename or "").suffix.lower()
    if suffix == ".pdf":
        pages = pdf_to_images(file_bytes)
        if not pages:
            raise ValueError("LiLT could not render PDF pages")
        image = pages[0].convert("RGB")
    else:
        image = Image.open(io.BytesIO(file_bytes)).convert("RGB")

    encoding = processor(
        image,
        return_tensors="pt",
        truncation=True,
        padding="max_length",
    )

    encoding = {k: v.to(DEVICE) for k, v in encoding.items()}

    with torch.no_grad():
        outputs = model(**encoding)

    logits = outputs.logits
    predictions = logits.argmax(-1).squeeze().tolist()

    probs = torch.softmax(logits, dim=-1)
    max_probs = probs.max(dim=-1).values.squeeze()

    tokens = processor.tokenizer.convert_ids_to_tokens(
        encoding["input_ids"].squeeze().tolist()
    )

    labels = [id2label[p] for p in predictions]

    # ---- TEXT ----
    text = _clean_tokens(tokens)

    # ---- CONFIDENCE ----
    confidence = float(max_probs.mean().item())

    # ---- FIELD EXTRACTION (REAL) ----
    fields = _group_entities(tokens, labels)

    return LiLTResult(
        text=text,
        confidence=confidence,
        fields=fields,
    )
