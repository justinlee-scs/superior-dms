from __future__ import annotations

from PIL import Image
import pytesseract

from .handwriting_model import get_handwriting_classifier


def _analyze_image(image: Image.Image) -> tuple[float, float, int]:
    ocr = pytesseract.image_to_data(
        image,
        output_type=pytesseract.Output.DICT,
        config="--oem 1 --psm 6",
    )
    confs: list[int] = []
    words: list[str] = []
    for text, conf in zip(ocr.get("text", []), ocr.get("conf", [])):
        if text and text.strip():
            words.append(text.strip())
        try:
            conf_val = int(conf)
        except (TypeError, ValueError):
            continue
        if conf_val >= 0:
            confs.append(conf_val)

    if not confs:
        return 0.0, 0.0, 0

    text = " ".join(words)
    total_chars = len(text)
    alpha_chars = sum(ch.isalpha() for ch in text)
    alpha_ratio = alpha_chars / total_chars if total_chars else 0.0
    mean_conf = sum(confs) / len(confs)
    return mean_conf, alpha_ratio, len(words)


def is_handwritten(images: list[Image.Image]) -> bool:
    """Detect whether document contains handwriting.

    Heuristic: handwriting tends to produce lower OCR confidence and a moderate
    amount of alphabetic content. We consider multiple pages and take a
    majority vote.

    Parameters:
        images (type=list[Image.Image]): Function argument used by this operation.
    """
    if not images:
        return False

    classifier = get_handwriting_classifier()
    if classifier is not None:
        return classifier.is_handwritten(images)

    votes = 0
    checked = 0
    for image in images[:3]:
        checked += 1
        mean_conf, alpha_ratio, word_count = _analyze_image(image)
        if word_count >= 5 and mean_conf < 45:
            votes += 1
            continue
        if word_count >= 5 and mean_conf < 55 and alpha_ratio > 0.30:
            votes += 1
            continue
        if word_count >= 10 and mean_conf < 60 and alpha_ratio > 0.35:
            votes += 1

    return votes >= max(1, checked // 2)
