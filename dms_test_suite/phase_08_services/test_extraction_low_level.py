from __future__ import annotations

import io
from types import SimpleNamespace

import pytest
from PIL import Image

from app.services.extraction import ocr_sync
from app.services.extraction.handwriting import is_handwritten
from app.services.extraction.icr import run_icr_model
from app.services.extraction.ocr import run_tesseract
from app.services.extraction.pdf import pdf_to_images
from app.services.extraction.providers import ExtractionResult
from app.services.extraction.tesseract_provider import TesseractProvider


def test_pdf_to_images_flattens_nested_lists(monkeypatch: pytest.MonkeyPatch) -> None:
    img1 = Image.new("RGB", (2, 2))
    img2 = Image.new("RGB", (2, 2))
    monkeypatch.setattr("app.services.extraction.pdf.convert_from_bytes", lambda _b: [img1, [img2]])

    images = pdf_to_images(b"%PDF-1.7")
    assert images == [img1, img2]


def test_run_tesseract_handles_text_confidence_and_invalid_conf(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = iter(
        [
            {"text": ["hello", " ", "world"], "conf": ["80", "-1", "90"]},
            {"text": ["ignored"], "conf": ["nanx"]},
        ]
    )
    monkeypatch.setattr("app.services.extraction.ocr.pytesseract.image_to_data", lambda *_a, **_k: next(calls))

    img1 = Image.new("RGB", (2, 2))
    img2 = Image.new("RGB", (2, 2))
    text, confidence = run_tesseract([img1, img2])

    assert text == "hello world\nignored"
    assert confidence == 85.0


def test_tesseract_provider_office_pdf_and_image_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = TesseractProvider()

    monkeypatch.setattr("app.services.extraction.tesseract_provider.extract_text_from_office_file", lambda *_a, **_k: "office text")
    office_result = provider.extract(b"zip", "file.docx")
    assert office_result.engine == "office_xml"
    assert office_result.confidence == 1.0

    monkeypatch.setattr("app.services.extraction.tesseract_provider.pdf_to_images", lambda _b: ["pdfimg"])
    monkeypatch.setattr("app.services.extraction.tesseract_provider.run_tesseract", lambda imgs: ("pdf text", 0.5))
    pdf_result = provider.extract(b"%PDF-1.7", "file.pdf")
    assert pdf_result.text == "pdf text"
    assert pdf_result.engine == "tesseract"

    img = Image.new("RGB", (2, 2))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    monkeypatch.setattr("app.services.extraction.tesseract_provider.run_tesseract", lambda imgs: ("img text", 0.9))
    img_result = provider.extract(buf.getvalue(), "img.png")
    assert img_result.text == "img text"
    assert img_result.confidence == 0.9


def test_ocr_sync_provider_selection_and_low_confidence_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    ocr_sync._build_ocr_provider.cache_clear()
    monkeypatch.setenv("OCR_PROVIDER", "invalid-provider")
    with pytest.raises(ValueError):
        ocr_sync._build_ocr_provider()

    ocr_sync._build_ocr_provider.cache_clear()
    monkeypatch.setenv("OCR_PROVIDER", "trocr")
    monkeypatch.setenv("TROCR_MODEL_PATH", "microsoft/trocr-base-handwritten")
    provider = ocr_sync.get_ocr_provider()
    assert provider.__class__.__name__ == "TrOCRProvider"

    # Office + low confidence returns primary result without ICR.
    primary = SimpleNamespace(
        extract=lambda **_k: ExtractionResult(text="office low", confidence=0.1, engine="tesseract", metadata={})
    )
    monkeypatch.setattr("app.services.extraction.ocr_sync.get_ocr_provider_safe", lambda: primary)
    result = ocr_sync.extract_with_fallback(b"zip-data", "file.docx", min_confidence=0.6)
    assert result.text == "office low"

    # Low confidence + engine tesseract should return primary directly.
    primary2 = SimpleNamespace(
        extract=lambda **_k: ExtractionResult(text="weak", confidence=0.1, engine="tesseract", metadata={})
    )
    monkeypatch.setattr("app.services.extraction.ocr_sync.get_ocr_provider_safe", lambda: primary2)
    monkeypatch.setattr("app.services.extraction.ocr_sync._to_images", lambda **_k: ["img"])
    monkeypatch.setattr("app.services.extraction.ocr_sync.is_handwritten", lambda _i: False)
    result2 = ocr_sync.extract_with_fallback(b"png-bytes", "img.png", min_confidence=0.6)
    assert result2.text == "weak"


def test_handwriting_and_icr_placeholders() -> None:
    img = Image.new("RGB", (1, 1))
    assert is_handwritten([img]) is False
    text, conf = run_icr_model([img])
    assert text == "handwritten text"
    assert conf == 0.90
