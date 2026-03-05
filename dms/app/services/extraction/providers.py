from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ExtractionResult:
    """Define the extraction result type.
    
    Parameters:
        text (type=str): Parameter.
        confidence (type=float): Parameter.
        engine (type=str): Parameter.
        model_version (type=str | None): Parameter.
        latency_ms (type=int | None): Parameter.
        raw_confidence (type=float | None): Parameter.
        metadata (type=dict[str, Any]): Parameter.
    """
    text: str
    confidence: float
    engine: str
    model_version: str | None = None
    latency_ms: int | None = None
    raw_confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class OCRProvider(Protocol):
    """Define the ocrprovider interface contract.
    
    Parameters:
        None.
    """
    def extract(self, file_bytes: bytes, filename: str) -> ExtractionResult:
        """Handle extract for this instance.

        Parameters:
            file_bytes (type=bytes): Raw file content used for validation or processing.
            filename (type=str): File or entity name used for storage and display.
        """
        ...
