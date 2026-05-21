#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

from datasets import load_dataset


def _normalize_label(label: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9]+", "_", (label or "").strip().lower()).strip("_")
    return clean or "O"


def _iter_cord_tokens(example: dict):
    # CORD v2 has OCR words and semantic classes under "valid_line"/"gt_parse" style structures.
    # This extractor is defensive to handle dataset schema drift.
    meta = example.get("meta") or {}
    image = example.get("image")
    if image is None:
        return []

    width, height = image.size
    if width <= 0 or height <= 0:
        return []

    rows = []

    # Prefer richer token-level annotations when available.
    gt_raw = example.get("ground_truth")
    if isinstance(gt_raw, str) and gt_raw.strip():
        try:
            gt = json.loads(gt_raw)
        except json.JSONDecodeError:
            gt = {}
    elif isinstance(gt_raw, dict):
        gt = gt_raw
    else:
        gt = {}

    valid_line = gt.get("valid_line") or []
    if valid_line:
        for li, line in enumerate(valid_line):
            category = _normalize_label(str(line.get("category") or "O"))
            words = line.get("words") or []
            for wi, w in enumerate(words):
                text = (w.get("text") or "").strip()
                quad = w.get("quad") or {}
                x1 = float(quad.get("x1", 0.0))
                y1 = float(quad.get("y1", 0.0))
                x3 = float(quad.get("x3", x1))
                y3 = float(quad.get("y3", y1))
                if not text:
                    continue
                x = max(0.0, min(1.0, x1 / width))
                y = max(0.0, min(1.0, y1 / height))
                w_norm = max(0.0, min(1.0, (x3 - x1) / width))
                h_norm = max(0.0, min(1.0, (y3 - y1) / height))
                rows.append((text, x, y, w_norm, h_norm, category))
        return rows

    # Fallback: unlabeled OCR words => O label
    words = example.get("words") or []
    for w in words:
        text = (w.get("text") or "").strip()
        box = w.get("box") or [0, 0, 0, 0]
        if not text or len(box) != 4:
            continue
        x1, y1, x2, y2 = [float(v) for v in box]
        x = max(0.0, min(1.0, x1 / width))
        y = max(0.0, min(1.0, y1 / height))
        w_norm = max(0.0, min(1.0, (x2 - x1) / width))
        h_norm = max(0.0, min(1.0, (y2 - y1) / height))
        rows.append((text, x, y, w_norm, h_norm, "O"))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="naver-clova-ix/cord-v2")
    parser.add_argument("--split", default="train")
    parser.add_argument("--max-samples", type=int, default=3000)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--image-dir", required=True)
    args = parser.parse_args()

    out_csv = Path(args.output_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    image_dir = Path(args.image_dir)
    image_dir.mkdir(parents=True, exist_ok=True)

    ds = load_dataset(args.dataset, split=args.split)
    n = min(len(ds), args.max_samples)

    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["text", "x", "y", "w", "h", "label", "task_id", "image_path"],
        )
        writer.writeheader()

        for i in range(n):
            ex = ds[i]
            img = ex.get("image")
            if img is None:
                continue

            img_path = image_dir / f"cord_{i:06d}.png"
            img.save(img_path)

            rows = _iter_cord_tokens(ex)
            task_id = f"cord_{i:06d}"
            for text, x, y, w_norm, h_norm, label in rows:
                writer.writerow(
                    {
                        "text": text,
                        "x": f"{x:.6f}",
                        "y": f"{y:.6f}",
                        "w": f"{w_norm:.6f}",
                        "h": f"{h_norm:.6f}",
                        "label": label,
                        "task_id": task_id,
                        "image_path": str(img_path),
                    }
                )

    print(f"Wrote {out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
