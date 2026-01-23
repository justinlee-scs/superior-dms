from typing import Tuple
from app.services.extraction.pdf import pdf_to_images
from app.services.extraction.ocr import run_tesseract


def extract_text_from_file(
    file_bytes: bytes,
    filename: str,
) -> Tuple[str, float]:
    """
    Synchronous OCR entry point.
    Returns (text, confidence).
    """

    if filename.lower().endswith(".pdf"):
        images = pdf_to_images(file_bytes)
    else:
        from PIL import Image
        import io

        images = [Image.open(io.BytesIO(file_bytes))]

    text, confidence = run_tesseract(images)

    return text or "", confidence or 0.0
