#!/usr/bin/env python3
"""
Converts mychen76/invoices-and-receipts_ocr_v1 to field_tokens.csv.
Adds invoice_number and company (seller) coverage missing from SROIE.

Usage:
    python scripts/prepare_mychen_invoices.py \
        --output-csv data/processed/mychen_field_tokens.csv
"""
from __future__ import annotations

import ast
import csv
import json
import re
from pathlib import Path
import argparse

from datasets import load_dataset

FIELD_MAP = {
    "invoice_no":        "invoice_number",
    "invoice_date":      "document_date",
    "seller":            "company",
    "client":            "bill_to",
    "total_gross_worth": "grand_total",
    "total_net_worth":   "grand_total",
}


def _parse_parsed_data(raw: str) -> dict:
    try:
        outer = json.loads(raw)
        inner_json = outer.get("json", "")
        if isinstance(inner_json, str):
            try:
                inner = ast.literal_eval(inner_json)
            except Exception:
                inner = {}
        else:
            inner = inner_json
        header = inner.get("header", {})
        summary = inner.get("summary", {})
        return {**header, "summary": summary}
    except Exception:
        return {}


def _parse_ocr_boxes(raw_data_str: str) -> list[tuple[str, list]]:
    try:
        raw = json.loads(raw_data_str)
        boxes_str = raw.get("ocr_boxes", "[]")
        boxes = ast.literal_eval(boxes_str)
        result = []
        for entry in boxes:
            if len(entry) != 2:
                continue
            quad, text_conf = entry
            text = text_conf[0] if isinstance(text_conf, (list, tuple)) else ""
            text = str(text).strip()
            if not text:
                continue
            result.append((text, quad))
        return result
    except Exception:
        return []


def _normalize_box(quad: list, img_w: float, img_h: float) -> tuple[float, float, float, float]:
    xs = [pt[0] for pt in quad]
    ys = [pt[1] for pt in quad]
    x1, y1 = min(xs), min(ys)
    x2, y2 = max(xs), max(ys)
    x = max(0.0, min(1.0, x1 / img_w))
    y = max(0.0, min(1.0, y1 / img_h))
    w = max(0.0, min(1.0, (x2 - x1) / img_w))
    h = max(0.0, min(1.0, (y2 - y1) / img_h))
    return x, y, w, h


def _norm_compare(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _find_span(ocr_words: list[str], value: str) -> set[int]:
    if not value:
        return set()

    def _match(search_value: str) -> set[int]:
        parts = [_norm_compare(p) for p in search_value.split() if _norm_compare(p)]
        if not parts:
            return set()
        normalized = [_norm_compare(w) for w in ocr_words]
        matched = set()
        for start in range(len(normalized)):
            if normalized[start] != parts[0]:
                continue
            pi, ti = 0, start
            while pi < len(parts) and ti < len(normalized):
                if normalized[ti] == parts[pi]:
                    pi += 1
                ti += 1
            if pi == len(parts):
                matched.update(range(start, ti))
        return matched

    # Try full value first
    result = _match(value)
    if result:
        return result

    # Fallback: try each word individually
    # Catches invoice numbers embedded in strings like "Invoice no: 40378170"
    for part in value.split():
        part = part.strip(":#.,")
        if len(part) >= 3:
            result = _match(part)
            if result:
                return result

    return set()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-csv", default="data/processed/mychen_field_tokens.csv")
    parser.add_argument("--max-samples", type=int, default=0)
    args = parser.parse_args()

    out_path = Path(args.output_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print("Loading mychen76/invoices-and-receipts_ocr_v1...")
    ds = load_dataset("mychen76/invoices-and-receipts_ocr_v1", split="train")
    n = min(len(ds), args.max_samples) if args.max_samples > 0 else len(ds)
    print(f"Processing {n} documents...")

    written = 0
    skipped = 0

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "text", "x", "y", "w", "h", "page", "label", "task_id", "filename", "image_path"
        ])
        writer.writeheader()

        for i in range(n):
            ex = ds[i]
            task_id = f"mychen_{str(ex.get('id', i)).zfill(6)}"

            image = ex.get("image")
            if image is None:
                skipped += 1
                continue
            img_w, img_h = image.size

            fields = _parse_parsed_data(ex.get("parsed_data", "{}"))
            summary = fields.pop("summary", {})

            field_values: dict[str, str] = {}
            for ds_key, label in FIELD_MAP.items():
                val = str(fields.get(ds_key) or summary.get(ds_key) or "").strip()
                if val and label not in field_values:
                    field_values[label] = val

            ocr_entries = _parse_ocr_boxes(ex.get("raw_data", "{}"))
            if not ocr_entries:
                skipped += 1
                continue

            ocr_words = [text for text, _ in ocr_entries]
            token_labels = ["O"] * len(ocr_words)
            for label, value in field_values.items():
                for idx in _find_span(ocr_words, value):
                    token_labels[idx] = label

            for (text, quad), label in zip(ocr_entries, token_labels):
                x, y, w, h = _normalize_box(quad, img_w, img_h)
                writer.writerow({
                    "text":       text,
                    "x":          f"{x:.6f}",
                    "y":          f"{y:.6f}",
                    "w":          f"{w:.6f}",
                    "h":          f"{h:.6f}",
                    "page":       "1",
                    "label":      label,
                    "task_id":    task_id,
                    "filename":   f"{task_id}.jpg",
                    "image_path": "",
                })
                written += 1

    print(f"Wrote {written} token rows to {out_path}")
    print(f"Skipped {skipped} documents")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())