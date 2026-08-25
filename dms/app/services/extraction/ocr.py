from __future__ import annotations

from collections import defaultdict
from math import isnan
from typing import Iterable

from PIL import Image
import pytesseract


def _safe_confidence(value: str) -> float | None:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return None
    if isnan(confidence) or confidence < 0:
        return None
    return confidence


def _value_at(values: list, index: int, default: int = 0) -> int:
    try:
        return int(values[index])
    except (IndexError, TypeError, ValueError):
        return default


def _group_words_by_line(data: dict[str, list], *, image_index: int) -> tuple[list[str], list[float]]:
    """Rebuild OCR text in reading order using Tesseract's line metadata."""
    grouped: dict[tuple[int, int, int, int], list[str]] = defaultdict(list)
    line_confidences: dict[tuple[int, int, int, int], list[float]] = defaultdict(list)

    for idx, text in enumerate(data.get("text", [])):
        word = str(text or "").strip()
        if not word:
            continue

        key = (
            image_index,
            _value_at(data.get("block_num", []), idx),
            _value_at(data.get("par_num", []), idx),
            _value_at(data.get("line_num", []), idx),
        )
        grouped[key].append(word)

        confidence = _safe_confidence(
            data.get("conf", [None])[idx] if idx < len(data.get("conf", [])) else None
        )
        if confidence is not None:
            line_confidences[key].append(confidence)

    lines: list[str] = []
    confidences: list[float] = []
    for key in sorted(grouped):
        line = " ".join(grouped[key]).strip()
        if not line:
            continue
        lines.append(line)
        if line_confidences.get(key):
            confidences.append(sum(line_confidences[key]) / len(line_confidences[key]))

    return lines, confidences


def run_tesseract(images: Iterable[Image.Image]) -> tuple[str, float]:
    """Runs OCR on a list of PIL Images.

    Parameters:
        images (type=Iterable[Image.Image]): Function argument used by this operation.
    """

    texts = []
    confidences = []

    for image_index, image in enumerate(images, start=1):
        data = pytesseract.image_to_data(
            image,
            output_type=pytesseract.Output.DICT,
        )

        lines, line_confs = _group_words_by_line(data, image_index=image_index)
        if lines:
            texts.append("\n".join(lines))
            confidences.extend(line_confs)

    full_text = "\n\n".join(texts)
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    return full_text, avg_confidence
