from __future__ import annotations

import io

import cv2
import numpy as np
from PIL import Image


def preprocess_image_bytes(file_bytes: bytes) -> bytes:
    """Apply OpenCV preprocessing and return PNG bytes."""
    image_array = np.frombuffer(file_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Could not decode image bytes.")

    processed = preprocess_bgr_image(image)
    ok, encoded = cv2.imencode(".png", processed)
    if not ok:
        raise ValueError("Could not encode preprocessed image.")
    return encoded.tobytes()


def preprocess_bgr_image(image: np.ndarray) -> np.ndarray:
    """Deskew, denoise, and adaptive-threshold an image."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, None, h=15, templateWindowSize=7, searchWindowSize=21)
    thresholded = cv2.adaptiveThreshold(
        denoised,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11,
    )
    return _deskew_binary(thresholded)


def preprocess_pil_image(image: Image.Image) -> Image.Image:
    """Preprocess a PIL image and return a PIL image."""
    rgb = image.convert("RGB")
    bgr = cv2.cvtColor(np.array(rgb), cv2.COLOR_RGB2BGR)
    processed_bgr = preprocess_bgr_image(bgr)
    processed_rgb = cv2.cvtColor(processed_bgr, cv2.COLOR_GRAY2RGB)
    return Image.fromarray(processed_rgb)


def _deskew_binary(binary: np.ndarray) -> np.ndarray:
    """Estimate skew angle from foreground pixels and rotate."""
    points = np.column_stack(np.where(binary < 250))
    if points.size == 0:
        return binary

    rect = cv2.minAreaRect(points.astype(np.float32))
    angle = rect[-1]
    if angle < -45:
        angle = 90 + angle
    angle = -angle

    h, w = binary.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(
        binary,
        matrix,
        (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )


def pil_to_png_bytes(image: Image.Image) -> bytes:
    """Serialize PIL image to PNG bytes."""
    buff = io.BytesIO()
    image.save(buff, format="PNG")
    return buff.getvalue()

