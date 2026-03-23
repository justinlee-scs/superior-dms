import pytest

pytest.importorskip("pytesseract")
pytest.importorskip("PIL")
from PIL import Image  # noqa: E402

from app.services.extraction import handwriting


def test_analyze_image_with_confs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        handwriting.pytesseract,
        "image_to_data",
        lambda *_a, **_k: {"text": ["Hello", " "], "conf": ["80", "50"]},
    )
    image = Image.new("RGB", (10, 10))
    mean_conf, alpha_ratio, word_count = handwriting._analyze_image(image)
    assert mean_conf == 65.0
    assert word_count == 1
    assert 0.0 < alpha_ratio <= 1.0


def test_handwriting_confidence_with_classifier(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Classifier:
        def predict_scores(self, _images):
            return [0.6, 0.4]

    monkeypatch.setattr(handwriting, "get_handwriting_classifier", lambda: _Classifier())
    image = Image.new("RGB", (10, 10))
    score = handwriting.handwriting_confidence([image, image])
    assert score == 0.5


def test_handwriting_confidence_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(handwriting, "get_handwriting_classifier", lambda: None)
    monkeypatch.setattr(handwriting, "_analyze_image", lambda *_a, **_k: (50.0, 0.5, 2))
    image = Image.new("RGB", (10, 10))
    score = handwriting.handwriting_confidence([image])
    assert 0.0 <= score <= 1.0
