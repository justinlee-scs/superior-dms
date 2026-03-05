from typing import List
from PIL import Image
import pytesseract


def run_tesseract(images: List[Image.Image]) -> tuple[str, float]:
    """Runs OCR on a list of PIL Images.

    Parameters:
        images (type=List[Image.Image]): Function argument used by this operation.
    """

    texts = []
    confidences = []

    for image in images:
        data = pytesseract.image_to_data(
            image,
            output_type=pytesseract.Output.DICT,
        )

        words = []
        word_confs = []

        for text, conf in zip(data["text"], data["conf"]):
            if text.strip():
                words.append(text)
                try:
                    word_confs.append(float(conf))
                except ValueError:
                    pass

        if words:
            texts.append(" ".join(words))
            if word_confs:
                confidences.append(sum(word_confs) / len(word_confs))

    full_text = "\n".join(texts)
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    return full_text, avg_confidence
