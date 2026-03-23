from types import SimpleNamespace

import pytest

pil = pytest.importorskip("PIL")
from PIL import Image  # noqa: E402

from app.services.extraction import icr


def test_run_icr_model_empty() -> None:
    assert icr.run_icr_model([]) == ("", 0.0)


def test_run_icr_model_aggregates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(icr, "_extract_from_image", lambda _img: ("text", 0.8))
    image = Image.new("RGB", (10, 10))
    text, confidence = icr.run_icr_model([image, image])
    assert text == "text\ntext"
    assert confidence == 0.8


def test_extract_from_image_uses_processor(monkeypatch: pytest.MonkeyPatch) -> None:
    torch = pytest.importorskip("torch")

    class _Processor:
        def __init__(self):
            self.called = False

        def __call__(self, **_kwargs):
            self.called = True
            return SimpleNamespace(pixel_values="pixels")

        def batch_decode(self, *_a, **_k):
            return ["hello"]

    class _Model:
        def generate(self, _):
            return ["ids"]

    processor = _Processor()
    model = _Model()
    monkeypatch.setattr(icr, "_load_trocr", lambda: ("model", processor, model))

    image = Image.new("RGB", (10, 10))
    text, confidence = icr._extract_from_image(image)
    assert processor.called is True
    assert text == "hello"
    assert confidence == 0.85


def test_load_trocr_uses_env(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Processor:
        @staticmethod
        def from_pretrained(name):
            return f"processor:{name}"

    class _Model:
        @staticmethod
        def from_pretrained(name):
            return f"model:{name}"

    dummy_module = SimpleNamespace(
        TrOCRProcessor=_Processor,
        VisionEncoderDecoderModel=_Model,
    )
    monkeypatch.setitem(__import__("sys").modules, "transformers", dummy_module)
    monkeypatch.setenv("TROCR_MODEL_PATH", "custom")
    icr._load_trocr.cache_clear()
    name, processor, model = icr._load_trocr()
    assert name == "custom"
    assert processor == "processor:custom"
    assert model == "model:custom"
