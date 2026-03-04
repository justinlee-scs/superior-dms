import importlib
import sys
import types
from types import SimpleNamespace

import pytest
from fastapi import HTTPException


@pytest.fixture
def processing_module(monkeypatch: pytest.MonkeyPatch):
    fake_worker = types.ModuleType("app.workers.processor")
    fake_worker.enqueue_processing = lambda _version_id: None
    monkeypatch.setitem(sys.modules, "app.workers.processor", fake_worker)

    module = importlib.import_module("app.api.processing")
    importlib.reload(module)
    return module


def test_process_document_not_found_raises(processing_module, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(processing_module.repositories, "get_document", lambda *_a, **_k: None, raising=False)

    with pytest.raises(HTTPException) as exc:
        processing_module.process_document("doc-1", db=object())
    assert exc.value.status_code == 404


def test_process_document_enqueues_current_version(processing_module, monkeypatch: pytest.MonkeyPatch):
    doc = SimpleNamespace(current_version_id="v-1")
    called = {"enqueued": None}
    monkeypatch.setattr(processing_module.repositories, "get_document", lambda *_a, **_k: doc, raising=False)
    monkeypatch.setattr(processing_module, "enqueue_processing", lambda vid: called.update(enqueued=vid))

    result = processing_module.process_document("doc-1", db=object())

    assert called["enqueued"] == "v-1"
    assert result == {"document_id": "doc-1", "status": "processing_started"}


def test_reprocess_document_resets_state_and_enqueues(processing_module, monkeypatch: pytest.MonkeyPatch):
    doc = SimpleNamespace(current_version_id="v-2")
    called = {"reset": None, "enqueued": None}
    monkeypatch.setattr(processing_module.repositories, "get_document", lambda *_a, **_k: doc, raising=False)
    monkeypatch.setattr(
        processing_module.repositories,
        "reset_processing_state",
        lambda _db, vid: called.update(reset=vid),
        raising=False,
    )
    monkeypatch.setattr(processing_module, "enqueue_processing", lambda vid: called.update(enqueued=vid))

    result = processing_module.reprocess_document("doc-2", db=object())

    assert called == {"reset": "v-2", "enqueued": "v-2"}
    assert result == {"document_id": "doc-2", "status": "reprocessing_started"}


def test_reprocess_document_not_found_raises(processing_module, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(processing_module.repositories, "get_document", lambda *_a, **_k: None, raising=False)

    with pytest.raises(HTTPException) as exc:
        processing_module.reprocess_document("doc-404", db=object())
    assert exc.value.status_code == 404
