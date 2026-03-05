from __future__ import annotations

import io
import time
from pathlib import Path

from PIL import Image

from app.services.extraction.office import OFFICE_EXTENSIONS, extract_text_from_office_file
from app.services.extraction.ocr import run_tesseract
from app.services.extraction.pdf import pdf_to_images
from app.services.extraction.providers import ExtractionResult, OCRProvider


class TesseractProvider(OCRProvider):
    """Define the tesseract provider type.
    
    Parameters:
        None.
    """
    def extract(self, file_bytes: bytes, filename: str) -> ExtractionResult:
        """Handle extract for this instance.

        Parameters:
            file_bytes (type=bytes): Raw file content used for validation or processing.
            filename (type=str): File or entity name used for storage and display.
        """
        start = time.perf_counter()
        suffix = Path(filename or "").suffix.lower()

        if suffix in OFFICE_EXTENSIONS:
            text = extract_text_from_office_file(file_bytes, filename) or ""
            latency_ms = int((time.perf_counter() - start) * 1000)
            return ExtractionResult(
                text=text,
                confidence=1.0,
                raw_confidence=1.0,
                engine="office_xml",
                model_version="builtin",
                latency_ms=latency_ms,
            )

        if suffix == ".pdf":
            images = pdf_to_images(file_bytes)
        else:
            images = [Image.open(io.BytesIO(file_bytes))]

        text, confidence = run_tesseract(images)
        normalized_text = text or ""
        normalized_confidence = confidence or 0.0
        latency_ms = int((time.perf_counter() - start) * 1000)

        return ExtractionResult(
            text=normalized_text,
            confidence=normalized_confidence,
            raw_confidence=normalized_confidence,
            engine="tesseract",
            model_version="pytesseract",
            latency_ms=latency_ms,
        )
