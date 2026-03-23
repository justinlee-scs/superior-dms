import pytest

from app.services.extraction import classify


def test_load_model_missing_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DOC_CLASS_MODEL_PATH", raising=False)
    classify._load_model.cache_clear()
    assert classify._load_model() is None


def test_load_model_with_joblib(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOC_CLASS_MODEL_PATH", "/tmp/model.joblib")
    monkeypatch.setattr(classify, "joblib", None, raising=False)
    classify._load_model.cache_clear()

    class _Joblib:
        @staticmethod
        def load(path):
            return {"loaded": path}

    monkeypatch.setitem(__import__("sys").modules, "joblib", _Joblib)
    model = classify._load_model()
    assert model == {"loaded": "/tmp/model.joblib"}
