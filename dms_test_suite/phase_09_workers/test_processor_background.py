from types import SimpleNamespace

import pytest

from app.workers import processor


def test_process_in_background_closes_session(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"processed": False, "closed": False}

    class _DB:
        def close(self):
            calls["closed"] = True

    monkeypatch.setattr(processor, "SessionLocal", lambda: _DB())
    monkeypatch.setattr(processor, "process_document_version", lambda *_a, **_k: calls.__setitem__("processed", True))

    processor._process_in_background("id")
    assert calls["processed"] is True
    assert calls["closed"] is True


def test_enqueue_processing_starts_thread(monkeypatch: pytest.MonkeyPatch) -> None:
    started = {"value": False}

    class _Thread:
        def __init__(self, *, target, args, daemon):
            self.target = target
            self.args = args
            self.daemon = daemon

        def start(self):
            started["value"] = True

    monkeypatch.setattr(processor.threading, "Thread", _Thread)
    processor.enqueue_processing("id")
    assert started["value"] is True
