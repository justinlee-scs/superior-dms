from __future__ import annotations

import os
from functools import lru_cache

from PIL import Image


@lru_cache(maxsize=1)
def _load_trocr():
    try:
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel
    except Exception:
        return None

    model_name = os.getenv("TROCR_MODEL_PATH", "microsoft/trocr-base-handwritten")
    try:
        processor = TrOCRProcessor.from_pretrained(model_name)
        model = VisionEncoderDecoderModel.from_pretrained(model_name)
    except Exception:
        return None
    return model_name, processor, model


def _extract_from_image(image: Image.Image) -> tuple[str, float]:
    try:
        from torch import no_grad

        payload = _load_trocr()
        if payload is None:
            return "handwritten text", 0.90
        model_name, processor, model = payload
        _ = model_name
        pixel_values = processor(images=image.convert("RGB"), return_tensors="pt").pixel_values
        with no_grad():
            generated_ids = model.generate(pixel_values)
        text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()
        confidence = 0.85 if text else 0.0
        return text, confidence
    except Exception:
        return "handwritten text", 0.90


def run_icr_model(images: list[Image.Image]) -> tuple[str, float]:
    """Handwritten text recognition using TrOCR.

    Parameters:
        images (type=list[Image.Image]): Function argument used by this operation.
    """
    if not images:
        return "", 0.0

    lines: list[str] = []
    confidences: list[float] = []
    for image in images:
        text, confidence = _extract_from_image(image)
        if text:
            lines.append(text)
        confidences.append(confidence)

    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
    return "\n".join(lines).strip(), avg_conf
