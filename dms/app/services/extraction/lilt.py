import io
from dataclasses import dataclass
from typing import Any, Dict, Optional

from PIL import Image

# HuggingFace / transformers
from transformers import LayoutLMv3Processor, LayoutLMv3ForTokenClassification
import torch


# ---- DATA STRUCTURE ----


@dataclass
class LiLTResult:
    text: str
    confidence: Optional[float]
    fields: Dict[str, Any]


# ---- MODEL LOAD (GLOBAL, LAZY INIT SAFE) ----

_PROCESSOR = None
_MODEL = None


def _load_model():
    global _PROCESSOR, _MODEL

    if _PROCESSOR is None or _MODEL is None:
        _PROCESSOR = LayoutLMv3Processor.from_pretrained(
            "microsoft/layoutlmv3-base",
            apply_ocr=True,
        )
        _MODEL = LayoutLMv3ForTokenClassification.from_pretrained(
            "microsoft/layoutlmv3-base"
        )
        _MODEL.eval()

    return _PROCESSOR, _MODEL


# ---- CORE FUNCTION ----


def run_lilt_model(
    *,
    file_bytes: bytes,
    filename: str,
) -> LiLTResult:
    processor, model = _load_model()

    image = Image.open(io.BytesIO(file_bytes)).convert("RGB")

    encoding = processor(
        image,
        return_tensors="pt",
        truncation=True,
        padding="max_length",
    )

    with torch.no_grad():
        outputs = model(**encoding)

    logits = outputs.logits
    predictions = logits.argmax(-1).squeeze().tolist()

    tokens = processor.tokenizer.convert_ids_to_tokens(
        encoding["input_ids"].squeeze().tolist()
    )

    # ---- SIMPLE TEXT RECONSTRUCTION ----
    words = []
    for token in tokens:
        if token.startswith("##"):
            if words:
                words[-1] += token[2:]
        else:
            words.append(token)

    text = " ".join(words)

    # ---- CONFIDENCE ----
    probs = torch.softmax(logits, dim=-1)
    max_probs = probs.max(dim=-1).values
    confidence = float(max_probs.mean().item())

    # ---- VERY BASIC FIELD EXTRACTION (PLACEHOLDER LOGIC) ----
    fields: Dict[str, Any] = {}

    # naive heuristics (replace later with trained head)
    lowered = text.lower()

    if "invoice" in lowered:
        fields["document_type"] = "invoice"

    if "total" in lowered:
        fields["has_total"] = True

    # due date placeholder (real model should output structured token labels)
    # you can later replace this with token classification parsing

    return LiLTResult(
        text=text,
        confidence=confidence,
        fields=fields,
    )
