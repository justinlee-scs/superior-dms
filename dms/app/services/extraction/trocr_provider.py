from __future__ import annotations

from app.services.extraction.providers import ExtractionResult, OCRProvider
from app.services.extraction.trocr_hf_provider import TrOCRHFProvider


class TrOCRProvider(OCRProvider):
    """TrOCR provider backed by Hugging Face transformers.
    
    Parameters:
        None.
    """

    def __init__(self, model_name_or_path: str):
        """Initialize the instance state.

        Parameters:
            model_name_or_path (type=str): Function argument used by this operation.
        """
        self.model_name_or_path = model_name_or_path
        self._delegate = TrOCRHFProvider(model_name_or_path=model_name_or_path)

    def extract(self, file_bytes: bytes, filename: str) -> ExtractionResult:
        """Handle extract for this instance.

        Parameters:
            file_bytes (type=bytes): Raw file content used for validation or processing.
            filename (type=str): File or entity name used for storage and display.
        """
        result = self._delegate.extract(file_bytes=file_bytes, filename=filename)
        result.metadata = {**result.metadata, "requested_provider": "trocr"}
        return result
