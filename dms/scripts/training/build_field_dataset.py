from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from app.services.extraction.opencv_preprocess import preprocess_pil_image


def _index_images(root: Path) -> dict[str, Path]:
    index: dict[str, Path] = {}
    for path in root.rglob("*"):
        if path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
            continue
        index.setdefault(path.name, path)
    return index


def _resolve_image_path(image_ref: str, index: dict[str, Path]) -> Path | None:
    if not image_ref:
        return None
    if image_ref.startswith("http"):
        name = Path(image_ref).name
        return index.get(name)
    if image_ref.startswith("/data/local-files/"):
        root = os.getenv("LOCAL_FILES_DOCUMENT_ROOT", "/home/justinlee/.LINUXPRACTICE/dms")
        rel = image_ref[len("/data/local-files/") :].lstrip("/")
        candidate = Path(root) / rel
        if candidate.exists():
            return candidate
    candidate = Path(image_ref)
    if candidate.exists():
        return candidate
    return index.get(Path(image_ref).name)


def _rectangles_for_task(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rects: list[dict[str, Any]] = []
    for res in results:
        if res.get("type") != "rectanglelabels":
            continue
        value = res.get("value", {}) or {}
        labels = value.get("rectanglelabels") or []
        if not labels:
            continue
        rects.append(
            {
                "label": labels[0],
                "x": float(value.get("x", 0)),
                "y": float(value.get("y", 0)),
                "w": float(value.get("width", 0)),
                "h": float(value.get("height", 0)),
                "original_width": float(res.get("original_width", 0) or 0),
                "original_height": float(res.get("original_height", 0) or 0),
            }
        )
    return rects


def _rect_to_abs(rect: dict[str, Any]) -> tuple[float, float, float, float]:
    width = rect["original_width"]
    height = rect["original_height"]
    x0 = rect["x"] / 100.0 * width
    y0 = rect["y"] / 100.0 * height
    w = rect["w"] / 100.0 * width
    h = rect["h"] / 100.0 * height
    return x0, y0, w, h


def _pick_label(x: float, y: float, rects: list[dict[str, Any]]) -> str:
    best = None
    best_area = None
    for rect in rects:
        x0, y0, w, h = _rect_to_abs(rect)
        if x < x0 or y < y0 or x > x0 + w or y > y0 + h:
            continue
        area = w * h
        if best is None or (best_area is not None and area < best_area):
            best = rect["label"]
            best_area = area
    return best or "O"


def _ocr_tokens(image: Image.Image) -> list[dict[str, Any]]:
    try:
        from pytesseract import Output
        import pytesseract
    except Exception:
        return []
    try:
        processed = preprocess_pil_image(image)
    except Exception:
        processed = image
    data = pytesseract.image_to_data(processed, output_type=Output.DICT)
    tokens: list[dict[str, Any]] = []
    width, height = processed.size
    for i, text in enumerate(data.get("text", [])):
        if not text or not str(text).strip():
            continue
        try:
            conf = float(data.get("conf", [0])[i])
        except Exception:
            conf = 0.0
        if conf < 0:
            continue
        x = float(data.get("left", [0])[i])
        y = float(data.get("top", [0])[i])
        w = float(data.get("width", [0])[i])
        h = float(data.get("height", [0])[i])
        tokens.append(
            {
                "text": str(text).strip(),
                "x": x / width if width else 0.0,
                "y": y / height if height else 0.0,
                "w": w / width if width else 0.0,
                "h": h / height if height else 0.0,
                "x_abs": x,
                "y_abs": y,
            }
        )
    return tokens


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--image-root", default="/home/justinlee/.LINUXPRACTICE/dms/output/training")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        tasks = json.load(f)

    image_root = Path(args.image_root)
    index = _index_images(image_root)

    rows: list[list[str]] = []
    for task in tasks:
        data = task.get("data", {}) or {}
        image_ref = data.get("image", "")
        image_path = _resolve_image_path(image_ref, index)
        if not image_path or not image_path.exists():
            continue
        annotations = task.get("annotations") or []
        if not annotations:
            continue
        results = annotations[0].get("result", []) or []
        rects = _rectangles_for_task(results)
        if not rects:
            continue

        image = Image.open(image_path).convert("RGB")
        tokens = _ocr_tokens(image)
        page = int(data.get("page") or 1)
        for token in tokens:
            label = _pick_label(token["x_abs"], token["y_abs"], rects)
            rows.append(
                [
                    token["text"],
                    f"{token['x']:.6f}",
                    f"{token['y']:.6f}",
                    f"{token['w']:.6f}",
                    f"{token['h']:.6f}",
                    str(page),
                    label,
                    str(task.get("id") or ""),
                    data.get("filename", ""),
                    str(image_path),
                ]
            )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["text", "x", "y", "w", "h", "page", "label", "task_id", "filename", "image_path"]
        )
        writer.writerows(rows)

    print(f"Saved {len(rows)} token rows to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
