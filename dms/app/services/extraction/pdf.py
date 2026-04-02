import logging
import os
from io import BytesIO
from typing import List

from pdf2image import convert_from_bytes
from PIL import Image

from app.services.extraction.opencv_preprocess import preprocess_pil_image

logger = logging.getLogger(__name__)


def _opencv_enabled() -> bool:
    return os.getenv("OCR_OPENCV_PDF", "true").strip().lower() in {"1", "true", "yes"}


def _maybe_preprocess(images: List[Image.Image]) -> List[Image.Image]:
    if not images or not _opencv_enabled():
        return images
    try:
        return [preprocess_pil_image(img) for img in images]
    except Exception as exc:
        logger.warning("OpenCV PDF preprocessing failed; using original images: %s", exc)
        return images


def pdf_to_images(file_bytes: bytes) -> List[Image.Image]:
    """Convert a PDF into a flat list of PIL Images (one per page).

    Parameters:
        file_bytes (type=bytes): Raw file content used for validation or processing.
    """

    images = convert_from_bytes(file_bytes)

    # convert_from_bytes already returns List[Image.Image],
    # but this ensures correctness if wrapped elsewhere
    flat_images: List[Image.Image] = []

    for img in images:
        if isinstance(img, list):
            flat_images.extend(img)
        else:
            flat_images.append(img)

    return _maybe_preprocess(flat_images)
