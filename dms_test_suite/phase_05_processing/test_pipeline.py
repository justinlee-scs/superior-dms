from types import SimpleNamespace

import pytest

from app.db.models.enums import ProcessingStatus
from app.processing.pipeline import process_document_version


class _FakeQuery:
    def __init__(self, version):
        self._version = version

    def filter(self, *_args, **_kwargs):
        return self

    def one_or_none(self):
        return self._version


class _FakeDB:
    def __init__(self, version):
        self._version = version
        self.commits = 0
        self.flushes = 0

    def query(self, *_args, **_kwargs):
        return _FakeQuery(self._version)

    def commit(self):
        self.commits += 1

    def flush(self):
        self.flushes += 1


def _version():
    return SimpleNamespace(
        id="v-1",
        document_id="doc-1",
        document=SimpleNamespace(filename="invoice.pdf", document_type="incoming_invoice", label_tags=[], due_date=None, workflow_notes=None),
        extracted_text=None,
        extraction=None,
        extraction_raw=None,
        ocr_meta={},
        storage_size_bytes=None,
        page_count=None,
        processing_status=None,
    )


def test_process_document_returns_when_version_missing() -> None:
    db = _FakeDB(version=None)

    process_document_version(db=db, version_id="missing", file_bytes=b"x", commit=True)

    assert db.commits == 0
    assert db.flushes == 0


def test_process_document_success_writes_extraction_and_tags(monkeypatch: pytest.MonkeyPatch) -> None:
    version = _version()
    db = _FakeDB(version=version)
    extraction = SimpleNamespace(
        text="invoice text",
        confidence=0.93,
        raw_confidence=0.89,
        engine="tesseract",
        model_version="pytesseract",
        latency_ms=87,
        metadata={"handwriting_confidence": 0.1, "icr_confidence": 0.2},
    )

    monkeypatch.setattr("app.processing.pipeline.list_rejected_tags", lambda _db: [])
    monkeypatch.setattr("app.processing.pipeline._supports_document_ocr", lambda _filename: False)
    monkeypatch.setattr("app.processing.pipeline.extract_fields", lambda *_args: {})
    monkeypatch.setattr("app.processing.pipeline.extract_text_with_metadata", lambda **_kwargs: extraction)
    monkeypatch.setattr("app.processing.pipeline.classify_document", lambda text: "invoice")
    monkeypatch.setattr("app.processing.pipeline.list_existing_tags", lambda _db: ["invoice", "project:alpha"])
    monkeypatch.setattr("app.processing.pipeline.create_tag_pool_entry", lambda **_k: _k["tag"])
    monkeypatch.setattr(
        "app.processing.pipeline.derive_tags",
        lambda *_args, **_kwargs: ["document_type:incoming_invoice", "invoice", "project:alpha", "company:acme"],
    )

    process_document_version(db=db, version_id="v-1", file_bytes=b"file-bytes", commit=True)

    assert version.extracted_text == "invoice text"
    assert version.document.document_type == "invoice"
    assert version.ocr_meta["confidence"] == 0.93
    assert version.ocr_meta["raw_confidence"] == 0.89
    assert version.ocr_meta["engine"] == "ocr_only"
    assert version.ocr_meta["model_version"] == "none"
    assert version.document.label_tags == [
        "company:acme",
        "invoice",
        "project:alpha",
    ]
    assert version.processing_status == ProcessingStatus.uploaded
    assert db.commits == 1
    assert db.flushes == 0


def test_process_document_failure_sets_failed_and_commits(monkeypatch: pytest.MonkeyPatch) -> None:
    version = _version()
    db = _FakeDB(version=version)

    def _raise(**_kwargs):
        raise RuntimeError("ocr crashed")

    monkeypatch.setattr("app.processing.pipeline.list_rejected_tags", lambda _db: [])
    monkeypatch.setattr("app.processing.pipeline.extract_text_with_metadata", _raise)

    with pytest.raises(RuntimeError):
        process_document_version(db=db, version_id="v-1", file_bytes=b"file-bytes", commit=True)

    assert version.processing_status == ProcessingStatus.failed
    assert db.commits == 1
    assert db.flushes == 0


def test_process_document_failure_sets_failed_and_flushes_when_commit_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    version = _version()
    db = _FakeDB(version=version)

    def _raise(**_kwargs):
        raise RuntimeError("ocr crashed")

    monkeypatch.setattr("app.processing.pipeline.list_rejected_tags", lambda _db: [])
    monkeypatch.setattr("app.processing.pipeline.extract_text_with_metadata", _raise)

    with pytest.raises(RuntimeError):
        process_document_version(db=db, version_id="v-1", file_bytes=b"file-bytes", commit=False)

    assert version.processing_status == ProcessingStatus.failed
    assert db.commits == 0
    assert db.flushes == 1


def test_process_document_success_flushes_when_commit_false(monkeypatch: pytest.MonkeyPatch) -> None:
    version = _version()
    db = _FakeDB(version=version)
    extraction = SimpleNamespace(
        text="ok",
        confidence=0.80,
        raw_confidence=0.80,
        engine="tesseract",
        model_version="v",
        latency_ms=1,
        metadata={},
    )
    monkeypatch.setattr("app.processing.pipeline.list_rejected_tags", lambda _db: [])
    monkeypatch.setattr("app.processing.pipeline._supports_document_ocr", lambda _filename: False)
    monkeypatch.setattr("app.processing.pipeline.extract_fields", lambda *_args: {})
    monkeypatch.setattr("app.processing.pipeline.extract_text_with_metadata", lambda **_kwargs: extraction)
    monkeypatch.setattr("app.processing.pipeline.classify_document", lambda _text: "unknown")
    monkeypatch.setattr("app.processing.pipeline.list_existing_tags", lambda _db: [])
    monkeypatch.setattr("app.processing.pipeline.create_tag_pool_entry", lambda **_k: _k["tag"])
    monkeypatch.setattr(
        "app.processing.pipeline.derive_tags",
        lambda *_a, **_k: ["document_type:document", "project:alpha", "company:acme"],
    )

    process_document_version(db=db, version_id="v-1", file_bytes=b"x", commit=False)

    assert version.processing_status == ProcessingStatus.uploaded
    assert db.commits == 0
    assert db.flushes == 1
