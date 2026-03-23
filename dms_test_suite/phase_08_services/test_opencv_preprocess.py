import pytest

cv2 = pytest.importorskip("cv2")
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

from app.services.extraction import opencv_preprocess as op


def test_preprocess_image_bytes_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(op.cv2, "imdecode", lambda *_a, **_k: None)
    with pytest.raises(ValueError):
        op.preprocess_image_bytes(b"data")


def test_preprocess_bgr_image_deskew(monkeypatch: pytest.MonkeyPatch) -> None:
    dummy = np.zeros((10, 10, 3), dtype=np.uint8)
    monkeypatch.setattr(op, "_deskew_binary", lambda binary: binary)
    out = op.preprocess_bgr_image(dummy)
    assert out is not None


def test_deskew_binary_no_points() -> None:
    binary = (np.ones((10, 10)) * 255).astype("uint8")
    result = op._deskew_binary(binary)
    assert (result == binary).all()


def test_pil_to_png_bytes() -> None:
    image = Image.new("RGB", (2, 2))
    data = op.pil_to_png_bytes(image)
    assert data.startswith(b"\x89PNG")


def test_preprocess_pil_image(monkeypatch: pytest.MonkeyPatch) -> None:
    image = Image.new("RGB", (2, 2))
    monkeypatch.setattr(op, "preprocess_bgr_image", lambda _img: np.zeros((2, 2), dtype=np.uint8))
    result = op.preprocess_pil_image(image)
    assert isinstance(result, Image.Image)
