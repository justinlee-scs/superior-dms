from types import SimpleNamespace

import pytest
from PIL import Image

from app.services.extraction.ocr_sync import (
    extract_text_from_file,
    extract_with_fallback,
    get_ocr_provider_safe,
    validate_input_file,
)
from app.services.extraction.providers import ExtractionResult
from app.services.extraction.trocr_provider import TrOCRProvider


def test_validate_input_file_guards_empty_and_extension() -> None:
    with pytest.raises(ValueError):
        validate_input_file(b"", "a.pdf")
    with pytest.raises(ValueError):
        validate_input_file(b"data", "a.exe")
    assert validate_input_file(b"data", "a.pdf") == ".pdf"
    assert validate_input_file(b"data", "noext") == ""


def test_get_ocr_provider_safe_falls_back_to_tesseract(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.extraction.ocr_sync._build_ocr_provider", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    provider = get_ocr_provider_safe()
    assert provider.__class__.__name__ == "TesseractProvider"


def test_extract_text_from_file_uses_metadata_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.extraction.ocr_sync.extract_text_with_metadata",
        lambda **_kwargs: ExtractionResult(text="abc", confidence=0.75, engine="x"),
    )

    text, confidence = extract_text_from_file(b"data", "doc.pdf")
    assert text == "abc"
    assert confidence == 0.75


def test_extract_with_fallback_returns_primary_when_confident(monkeypatch: pytest.MonkeyPatch) -> None:
    primary = SimpleNamespace(
        extract=lambda **_kwargs: ExtractionResult(
            text="primary",
            confidence=0.95,
            raw_confidence=0.91,
            engine="trocr",
            model_version="v1",
            latency_ms=10,
        )
    )
    monkeypatch.setattr("app.services.extraction.ocr_sync.get_ocr_provider_safe", lambda: primary)

    result = extract_with_fallback(b"%PDF-1.7", "doc.pdf", min_confidence=0.6)
    assert result.text == "primary"
    assert result.engine == "trocr"


def test_extract_with_fallback_uses_icr_on_low_confidence_handwriting(monkeypatch: pytest.MonkeyPatch) -> None:
    primary = SimpleNamespace(
        extract=lambda **_kwargs: ExtractionResult(
            text="weak",
            confidence=0.20,
            raw_confidence=0.20,
            engine="trocr",
            model_version="v1",
            latency_ms=25,
            metadata={"source": "primary"},
        )
    )
    monkeypatch.setattr("app.services.extraction.ocr_sync.get_ocr_provider_safe", lambda: primary)
    monkeypatch.setattr("app.services.extraction.ocr_sync._to_images", lambda **_kwargs: ["img"])
    monkeypatch.setattr("app.services.extraction.ocr_sync.is_handwritten", lambda _images: True)
    monkeypatch.setattr("app.services.extraction.ocr_sync.run_icr_model", lambda _images: ("icr text", 0.9))

    result = extract_with_fallback(b"imagebytes", "img.png", min_confidence=0.6)
    assert result.text == "icr text"
    assert result.confidence == 0.9
    assert result.engine.endswith("+icr_fallback")
    assert result.metadata["fallback_reason"] == "low_confidence_handwriting"


def test_extract_with_fallback_uses_tesseract_when_primary_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    primary = SimpleNamespace(extract=lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("fail")))
    tesseract_result = ExtractionResult(text="fallback", confidence=0.7, engine="tesseract", metadata={})
    fallback = SimpleNamespace(extract=lambda **_kwargs: tesseract_result)
    monkeypatch.setattr("app.services.extraction.ocr_sync.get_ocr_provider_safe", lambda: primary)
    monkeypatch.setattr("app.services.extraction.ocr_sync.TesseractProvider", lambda: fallback)

    result = extract_with_fallback(b"imagebytes", "img.png", min_confidence=0.6)
    assert result.text == "fallback"
    assert result.metadata["fallback_reason"] == "primary_provider_error"


def test_trocr_provider_preserves_metadata_and_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.extraction.tesseract_provider.TesseractProvider.extract",
        lambda self, **_kwargs: ExtractionResult(text="t", confidence=0.8, raw_confidence=0.75, engine="tesseract", metadata={}),
    )
    provider = TrOCRProvider(model_name_or_path="microsoft/trocr-base-handwritten")
    result = provider.extract(b"data", "x.png")

    assert result.text == "t"
    assert result.metadata["requested_provider"] == "trocr"
    assert result.metadata["fallback_reason"] == "trocr_not_implemented"


def test_ocr_sync_helpers_and_low_confidence_fallback_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    import io

    from app.services.extraction import ocr_sync

    # _to_images path for PDF and image files.
    marker = object()
    monkeypatch.setattr("app.services.extraction.ocr_sync.pdf_to_images", lambda _b: [marker])
    assert ocr_sync._to_images(b"%PDF-1.7", ".pdf") == [marker]

    img = Image.new("RGB", (2, 2))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    opened = ocr_sync._to_images(buf.getvalue(), ".png")
    assert len(opened) == 1
    assert opened[0].size == (2, 2)

    # _build_ocr_provider default branch returns tesseract.
    ocr_sync._build_ocr_provider.cache_clear()
    monkeypatch.setenv("OCR_PROVIDER", "tesseract")
    monkeypatch.setattr("app.services.extraction.ocr_sync.TesseractProvider", lambda: "tesseract-provider")
    assert ocr_sync._build_ocr_provider() == "tesseract-provider"
    ocr_sync._build_ocr_provider.cache_clear()

    # extract_text_with_metadata delegates to extract_with_fallback.
    sentinel = ExtractionResult(text="delegated", confidence=0.5, engine="x")
    original_extract_with_fallback = ocr_sync.extract_with_fallback
    monkeypatch.setattr("app.services.extraction.ocr_sync.extract_with_fallback", lambda **_k: sentinel)
    assert ocr_sync.extract_text_with_metadata(b"data", "a.png") is sentinel
    monkeypatch.setattr("app.services.extraction.ocr_sync.extract_with_fallback", original_extract_with_fallback)

    # Low confidence, non-handwritten, non-tesseract -> fallback tesseract branch.
    primary = SimpleNamespace(
        extract=lambda **_kwargs: ExtractionResult(
            text="weak",
            confidence=0.2,
            raw_confidence=0.2,
            engine="trocr",
            model_version="v1",
            latency_ms=2,
            metadata={},
        )
    )
    fallback_result = ExtractionResult(text="fallback", confidence=0.6, engine="tesseract", metadata={})
    monkeypatch.setattr("app.services.extraction.ocr_sync.get_ocr_provider_safe", lambda: primary)
    monkeypatch.setattr("app.services.extraction.ocr_sync._to_images", lambda **_k: ["img"])
    monkeypatch.setattr("app.services.extraction.ocr_sync.is_handwritten", lambda _images: False)
    monkeypatch.setattr(
        "app.services.extraction.ocr_sync.TesseractProvider",
        lambda: SimpleNamespace(extract=lambda **_kwargs: fallback_result),
    )
    result = ocr_sync.extract_with_fallback(b"img-bytes", "img.png", min_confidence=0.9)
    assert result.text == "fallback"
    assert result.metadata["fallback_reason"] == "low_confidence"
