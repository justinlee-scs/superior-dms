from types import SimpleNamespace

import pytest

from app.db.models.enums import DocumentClass, ProcessingStatus
from app.workers.processor import process_document_version


class _FakeDB:
    def __init__(self, version):
        self._version = version
        self.commits = 0

    def get(self, _model, _version_id):
        return self._version

    def commit(self):
        self.commits += 1


def _version():
    return SimpleNamespace(
        id="v-1",
        document=SimpleNamespace(filename="invoice.pdf", document_type="incoming_invoice"),
        processing_status=None,
    )


def test_process_document_version_returns_when_missing_version() -> None:
    db = _FakeDB(version=None)

    process_document_version(db=db, version_id="missing")

    assert db.commits == 0


def test_process_document_version_uses_tesseract_path(monkeypatch: pytest.MonkeyPatch) -> None:
    version = _version()
    db = _FakeDB(version=version)
    recorded = {}

    monkeypatch.setattr("app.workers.processor.load_document_version_bytes", lambda *_args, **_kwargs: b"%PDF-1.7")
    monkeypatch.setattr("app.workers.processor.pdf_to_images", lambda _bytes: ["img"])
    monkeypatch.setattr("app.workers.processor.run_tesseract", lambda _images: ("ocr text", 0.92))
    monkeypatch.setattr("app.workers.processor.run_icr_model", lambda _images: ("icr text", 0.80))
    monkeypatch.setattr("app.workers.processor.classify_document", lambda _text: DocumentClass.INVOICE)
    monkeypatch.setattr("app.workers.processor.list_existing_tags", lambda _db: ["invoice"])
    monkeypatch.setattr(
        "app.workers.processor.derive_tags",
        lambda *_args, **_kwargs: ["document_type:incoming_invoice", "invoice"],
    )

    def _capture_update(**kwargs):
        recorded.update(kwargs)

    monkeypatch.setattr("app.workers.processor.update_processing_results", _capture_update)

    process_document_version(db=db, version_id="v-1")

    assert recorded["version_id"] == "v-1"
    assert recorded["extracted_text"] == "ocr text"
    assert recorded["classification"] == DocumentClass.INVOICE
    assert recorded["confidence"] == 0.92
    assert recorded["ocr_raw_confidence"] == 0.92
    assert recorded["ocr_engine"] == "tesseract"
    assert recorded["ocr_model_version"] == "pytesseract"
    assert recorded["tags"] == ["document_type:incoming_invoice", "invoice"]
    assert isinstance(recorded["ocr_latency_ms"], int)
    assert recorded["ocr_latency_ms"] >= 0


def test_process_document_version_falls_back_to_icr(monkeypatch: pytest.MonkeyPatch) -> None:
    version = _version()
    db = _FakeDB(version=version)
    recorded = {}

    monkeypatch.setattr("app.workers.processor.load_document_version_bytes", lambda *_args, **_kwargs: b"%PDF-1.7")
    monkeypatch.setattr("app.workers.processor.pdf_to_images", lambda _bytes: ["img"])
    monkeypatch.setattr("app.workers.processor.run_tesseract", lambda _images: ("", 0.10))
    monkeypatch.setattr("app.workers.processor.run_icr_model", lambda _images: ("icr text", 0.88))
    monkeypatch.setattr("app.workers.processor.classify_document", lambda _text: DocumentClass.RECEIPT)
    monkeypatch.setattr("app.workers.processor.list_existing_tags", lambda _db: [])
    monkeypatch.setattr("app.workers.processor.derive_tags", lambda *_args, **_kwargs: ["receipt"])
    monkeypatch.setattr("app.workers.processor.update_processing_results", lambda **kwargs: recorded.update(kwargs))

    process_document_version(db=db, version_id="v-1")

    assert recorded["extracted_text"] == "icr text"
    assert recorded["confidence"] == 0.88
    assert recorded["ocr_raw_confidence"] == 0.10
    assert recorded["ocr_engine"] == "tesseract+icr_fallback"
    assert recorded["ocr_model_version"] == "pytesseract+placeholder_icr"


def test_process_document_version_marks_failed_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    version = _version()
    db = _FakeDB(version=version)

    monkeypatch.setattr(
        "app.workers.processor.load_document_version_bytes",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("load failed")),
    )

    with pytest.raises(RuntimeError):
        process_document_version(db=db, version_id="v-1")

    assert version.processing_status == ProcessingStatus.failed
    assert db.commits == 1
