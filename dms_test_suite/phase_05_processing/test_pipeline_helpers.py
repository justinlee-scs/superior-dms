import pytest

from app.processing import pipeline


def test_label_studio_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LABEL_STUDIO_ENABLED", "true")
    assert pipeline._label_studio_enabled() is True
    monkeypatch.setenv("LABEL_STUDIO_ENABLED", "false")
    assert pipeline._label_studio_enabled() is False


def test_notify_label_studio_missing_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LABEL_STUDIO_ENABLED", "true")
    monkeypatch.delenv("LABEL_STUDIO_URL", raising=False)
    monkeypatch.delenv("LABEL_STUDIO_API_TOKEN", raising=False)
    monkeypatch.delenv("LABEL_STUDIO_PROJECT_ID", raising=False)

    warnings = []
    monkeypatch.setattr(pipeline.logger, "warning", lambda msg, *_args: warnings.append(msg))

    pipeline._notify_label_studio(document_id="1", filename="a.pdf", text="hello")
    assert warnings


def test_notify_label_studio_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LABEL_STUDIO_ENABLED", "true")
    monkeypatch.setenv("LABEL_STUDIO_URL", "http://localhost/")
    monkeypatch.setenv("LABEL_STUDIO_API_TOKEN", "token")
    monkeypatch.setenv("LABEL_STUDIO_PROJECT_ID", "2")

    created = {"called": False}

    class _Client:
        def __init__(self, _config):
            pass

        def create_task_for_document(self, doc_id, filename, text):
            created["called"] = True
            created["doc_id"] = doc_id
            created["filename"] = filename
            created["text"] = text

    monkeypatch.setattr(pipeline, "LabelStudioClient", _Client)
    monkeypatch.setattr(pipeline, "LabelStudioConfig", lambda **_k: object())

    pipeline._notify_label_studio(document_id="1", filename="a.pdf", text="hello")
    assert created["called"] is True
