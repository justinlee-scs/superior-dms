import io
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Tuple

from PIL import Image

from app.services.extraction.handwriting import is_handwritten
from app.services.extraction.icr import run_icr_model
from app.services.extraction.office import OFFICE_EXTENSIONS
from app.services.extraction.providers import ExtractionResult, OCRProvider
from app.services.extraction.pdf import pdf_to_images
from app.services.extraction.tesseract_provider import TesseractProvider
from app.services.extraction.trocr_provider import TrOCRProvider
# Optional (disabled): production TrOCR provider + OpenCV preprocessing.
# from app.services.extraction.trocr_hf_provider import TrOCRHFProvider
# from app.services.extraction.opencv_preprocess import preprocess_image_bytes

logger = logging.getLogger(__name__)

SUPPORTED_IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".tif",
    ".tiff",
    ".bmp",
    ".gif",
    ".webp",
}


def validate_input_file(file_bytes: bytes, filename: str) -> str:
    """Validate input file.

    Parameters:
        file_bytes (type=bytes): Raw file content used for validation or processing.
        filename (type=str): File or entity name used for storage and display.
    """
    if not file_bytes:
        raise ValueError("Input file is empty.")

    suffix = Path(filename or "").suffix.lower()
    if not suffix:
        return suffix

    supported_extensions = OFFICE_EXTENSIONS | SUPPORTED_IMAGE_EXTENSIONS | {".pdf"}
    if suffix not in supported_extensions:
        raise ValueError(f"Unsupported file type '{suffix}'.")

    return suffix


def _to_images(file_bytes: bytes, suffix: str) -> list[Image.Image]:
    """Handle to images.

    Parameters:
        file_bytes (type=bytes): Raw file content used for validation or processing.
        suffix (type=str): Function argument used by this operation.
    """
    if suffix == ".pdf":
        return pdf_to_images(file_bytes)
    return [Image.open(io.BytesIO(file_bytes))]


@lru_cache(maxsize=1)
def _build_ocr_provider() -> OCRProvider:
    """Handle build ocr provider.

    Parameters:
        None.
    """
    provider = os.getenv("OCR_PROVIDER", "tesseract").strip().lower()

    # Optional (disabled):
    # if provider == "trocr_hf":
    #     model = os.getenv("TROCR_MODEL_PATH", "microsoft/trocr-base-handwritten")
    #     return TrOCRHFProvider(model_name_or_path=model)

    if provider == "trocr":
        model = os.getenv("TROCR_MODEL_PATH", "microsoft/trocr-base-handwritten")
        return TrOCRProvider(model_name_or_path=model)

    if provider != "tesseract":
        raise ValueError(f"Unsupported OCR_PROVIDER '{provider}'.")

    return TesseractProvider()


def get_ocr_provider() -> OCRProvider:
    """Return ocr provider.

    Parameters:
        None.
    """
    return _build_ocr_provider()


def get_ocr_provider_safe() -> OCRProvider:
    """Return ocr provider safe.

    Parameters:
        None.
    """
    try:
        return _build_ocr_provider()
    except Exception as exc:
        logger.warning("OCR provider init failed, falling back to tesseract: %s", exc)
        return TesseractProvider()


def extract_text_from_file(
    file_bytes: bytes,
    filename: str,
) -> Tuple[str, float]:
    """Synchronous OCR entry point.

    Parameters:
        file_bytes (type=bytes): Raw file content used for validation or processing.
        filename (type=str): File or entity name used for storage and display.
    """

    result = extract_text_with_metadata(file_bytes=file_bytes, filename=filename)
    return result.text or "", result.confidence or 0.0


def extract_text_with_metadata(
    file_bytes: bytes,
    filename: str,
) -> ExtractionResult:
    """Extract text with metadata.

    Parameters:
        file_bytes (type=bytes): Raw file content used for validation or processing.
        filename (type=str): File or entity name used for storage and display.
    """
    return extract_with_fallback(file_bytes=file_bytes, filename=filename)


def extract_with_fallback(
    file_bytes: bytes,
    filename: str,
    *,
    min_confidence: float | None = None,
) -> ExtractionResult:
    """Extract with fallback.

    Parameters:
        file_bytes (type=bytes): Raw file content used for validation or processing.
        filename (type=str): File or entity name used for storage and display.
        min_confidence (type=float | None, default=None): Function argument used by this operation.
    """
    suffix = validate_input_file(file_bytes=file_bytes, filename=filename)
    threshold = min_confidence if min_confidence is not None else float(
        os.getenv("OCR_MIN_CONFIDENCE", "0.60")
    )

    # Optional (disabled): preprocess image bytes with OpenCV before OCR provider.
    # if suffix in SUPPORTED_IMAGE_EXTENSIONS:
    #     try:
    #         file_bytes = preprocess_image_bytes(file_bytes)
    #     except Exception as exc:
    #         logger.warning("OpenCV preprocess failed; using original bytes: %s", exc)

    primary = get_ocr_provider_safe()
    try:
        result = primary.extract(file_bytes=file_bytes, filename=filename)
    except Exception as exc:
        logger.warning("Primary OCR provider failed: %s", exc)
        result = TesseractProvider().extract(file_bytes=file_bytes, filename=filename)
        result.metadata["fallback_reason"] = "primary_provider_error"
        return result

    if result.confidence >= threshold:
        return result

    # For low-confidence OCR, only image/pdf files can use ICR fallback.
    if suffix in OFFICE_EXTENSIONS:
        return result

    images = _to_images(file_bytes=file_bytes, suffix=suffix)
    if is_handwritten(images):
        icr_text, icr_confidence = run_icr_model(images)
        if icr_confidence >= result.confidence:
            return ExtractionResult(
                text=icr_text or "",
                confidence=icr_confidence or 0.0,
                raw_confidence=icr_confidence or 0.0,
                engine=f"{result.engine}+icr_fallback",
                model_version=result.model_version,
                latency_ms=result.latency_ms,
                metadata={**result.metadata, "fallback_reason": "low_confidence_handwriting"},
            )

    if result.engine == "tesseract":
        return result

    fallback = TesseractProvider().extract(file_bytes=file_bytes, filename=filename)
    fallback.metadata["fallback_reason"] = "low_confidence"
    return fallback
