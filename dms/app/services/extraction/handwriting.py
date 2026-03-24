from __future__ import annotations

from PIL import Image
import pytesseract

from .handwriting_model import get_handwriting_classifier


def _analyze_image(image: Image.Image) -> tuple[float, float, int]:
    try:
        ocr = pytesseract.image_to_data(
            image,
            output_type=pytesseract.Output.DICT,
            config="--oem 1 --psm 6",
        )
    except Exception:
        return 0.0, 0.0, 0
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


def handwriting_confidence(images: list[Image.Image]) -> float:
    """Detect whether document contains handwriting.

    Heuristic: handwriting tends to produce lower OCR confidence and a moderate
    amount of alphabetic content. We consider multiple pages and take a
    normalized score in [0, 1].

    Parameters:
        images (type=list[Image.Image]): Function argument used by this operation.
    """
    if not images:
        return 0.0

    classifier = get_handwriting_classifier()
    if classifier is not None:
        scores = classifier.predict_scores(images)
        if not scores:
            return 0.0
        return float(sum(scores) / len(scores))

    scores: list[float] = []
    for image in images[:3]:
        mean_conf, alpha_ratio, word_count = _analyze_image(image)
        if word_count == 0:
            scores.append(0.0)
            continue
        base = max(0.0, min(1.0, (60.0 - mean_conf) / 30.0))
        score = base * (0.5 + min(1.0, alpha_ratio))
        scores.append(max(0.0, min(1.0, score)))

    if not scores:
        return 0.0
    return float(sum(scores) / len(scores))


def is_handwritten(images: list[Image.Image]) -> bool:
    return handwriting_confidence(images) >= 0.5
