from __future__ import annotations

from app.services.extraction.providers import ExtractionResult, OCRProvider
from app.services.extraction.tesseract_provider import TesseractProvider


class TrOCRProvider(OCRProvider):
    """
    Phase-1 scaffold for TrOCR integration.
    Intentionally not active by default.
    """

    def __init__(self, model_name_or_path: str):
        self.model_name_or_path = model_name_or_path
        self._fallback = TesseractProvider()

    def extract(self, file_bytes: bytes, filename: str) -> ExtractionResult:
        # MVP behavior: route through tesseract while preserving intent metadata.
        result = self._fallback.extract(file_bytes=file_bytes, filename=filename)
        merged_metadata = dict(result.metadata)
        merged_metadata["requested_provider"] = "trocr"
        merged_metadata["trocr_model"] = self.model_name_or_path
        merged_metadata["fallback_reason"] = "trocr_not_implemented"

        return ExtractionResult(
            text=result.text,
            confidence=result.confidence,
            raw_confidence=result.raw_confidence,
            engine=result.engine,
            model_version=result.model_version,
            latency_ms=result.latency_ms,
            metadata=merged_metadata,
        )
