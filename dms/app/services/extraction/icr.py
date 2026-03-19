from __future__ import annotations

import os
from functools import lru_cache

from PIL import Image


@lru_cache(maxsize=1)
def _load_trocr():
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel

    model_name = os.getenv("TROCR_MODEL_PATH", "microsoft/trocr-base-handwritten")
    processor = TrOCRProcessor.from_pretrained(model_name)
    model = VisionEncoderDecoderModel.from_pretrained(model_name)
    return model_name, processor, model


def _extract_from_image(image: Image.Image) -> tuple[str, float]:
    from torch import no_grad

    model_name, processor, model = _load_trocr()
    _ = model_name
    pixel_values = processor(images=image.convert("RGB"), return_tensors="pt").pixel_values
    with no_grad():
        generated_ids = model.generate(pixel_values)
    text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()
    confidence = 0.85 if text else 0.0
    return text, confidence


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
