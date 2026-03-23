import pytest

torch = pytest.importorskip("torch")

from app.services.extraction import handwriting_model


def test_load_model_invalid_extension() -> None:
    with pytest.raises(ValueError):
        handwriting_model._load_model("model.bin")


def test_get_handwriting_classifier_missing_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HANDWRITING_MODEL_PATH", raising=False)
    handwriting_model.get_handwriting_classifier.cache_clear()
    assert handwriting_model.get_handwriting_classifier() is None


def test_load_model_pt_path(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    model_path = tmp_path / "model.pt"
    model_path.write_bytes(b"fake")

    class _Model:
        def __init__(self):
            self.loaded = False

        def load_state_dict(self, _state):
            self.loaded = True

        def eval(self):
            return self

    monkeypatch.setattr(handwriting_model, "_SimpleCNN", _Model)
    monkeypatch.setattr(handwriting_model.torch, "load", lambda *_a, **_k: {"state_dict": {}})

    model = handwriting_model._load_model(str(model_path))
    assert isinstance(model, _Model)
    assert model.loaded is True
