from typing import Tuple
from pathlib import Path
from app.services.extraction.pdf import pdf_to_images
from app.services.extraction.ocr import run_tesseract
from app.services.extraction.office import (
    OFFICE_EXTENSIONS,
    extract_text_from_office_file,
)


def extract_text_from_file(
    file_bytes: bytes,
    filename: str,
) -> Tuple[str, float]:
    """
    Synchronous OCR entry point.
    Returns (text, confidence).
    """

    suffix = Path(filename or "").suffix.lower()

    if suffix in OFFICE_EXTENSIONS:
        text = extract_text_from_office_file(file_bytes, filename)
        return text or "", 1.0

    if suffix == ".pdf":
        images = pdf_to_images(file_bytes)
    else:
        from PIL import Image
        import io

        images = [Image.open(io.BytesIO(file_bytes))]

    text, confidence = run_tesseract(images)

    return text or "", confidence or 0.0
