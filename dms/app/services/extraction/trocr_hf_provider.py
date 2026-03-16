from __future__ import annotations

import io
import time
from pathlib import Path

from PIL import Image

from app.services.extraction.office import OFFICE_EXTENSIONS, extract_text_from_office_file
from app.services.extraction.pdf import pdf_to_images
from app.services.extraction.providers import ExtractionResult, OCRProvider


class TrOCRHFProvider(OCRProvider):
    """TrOCR provider backed by Hugging Face transformers."""

    def __init__(self, model_name_or_path: str):
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel

        self.model_name_or_path = model_name_or_path
        self.processor = TrOCRProcessor.from_pretrained(model_name_or_path)
        self.model = VisionEncoderDecoderModel.from_pretrained(model_name_or_path)

    def extract(self, file_bytes: bytes, filename: str) -> ExtractionResult:
        suffix = Path(filename or "").suffix.lower()
        start = time.perf_counter()

        if suffix in OFFICE_EXTENSIONS:
            text = extract_text_from_office_file(file_bytes=file_bytes, filename=filename) or ""
            latency_ms = int((time.perf_counter() - start) * 1000)
            return ExtractionResult(
                text=text,
                confidence=0.90 if text else 0.0,
                raw_confidence=0.90 if text else 0.0,
                engine="trocr+office_native",
                model_version=self.model_name_or_path,
                latency_ms=latency_ms,
                metadata={"pages": 1, "source": "office-parser"},
            )

        images = self._to_images(file_bytes=file_bytes, suffix=suffix)
        lines: list[str] = []
        confidences: list[float] = []

        for image in images:
            text, confidence = self._extract_from_image(image)
            if text:
                lines.append(text)
            confidences.append(confidence)

        latency_ms = int((time.perf_counter() - start) * 1000)
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
        return ExtractionResult(
            text="\n".join(lines).strip(),
            confidence=avg_conf,
            raw_confidence=avg_conf,
            engine="trocr",
            model_version=self.model_name_or_path,
            latency_ms=latency_ms,
            metadata={"pages": len(images)},
        )

    def _to_images(self, *, file_bytes: bytes, suffix: str) -> list[Image.Image]:
        if suffix == ".pdf":
            return pdf_to_images(file_bytes)
        return [Image.open(io.BytesIO(file_bytes)).convert("RGB")]

    def _extract_from_image(self, image: Image.Image) -> tuple[str, float]:
        from torch import no_grad

        pixel_values = self.processor(images=image, return_tensors="pt").pixel_values
        with no_grad():
            generated_ids = self.model.generate(pixel_values)
        text = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        confidence = 0.85 if text.strip() else 0.0
        return text.strip(), confidence

