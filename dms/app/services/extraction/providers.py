from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ExtractionResult:
    text: str
    confidence: float
    engine: str
    model_version: str | None = None
    latency_ms: int | None = None
    raw_confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class OCRProvider(Protocol):
    def extract(self, file_bytes: bytes, filename: str) -> ExtractionResult:
        ...
