#!/usr/bin/env python3
"""
Converts the darentang/sroie HuggingFace dataset directly to field_tokens.csv
in the same format as prepare_hf_lilt_data.py / prepare_sroie_invoice_warmstart.py.

No OCR needed — SROIE already has token-level annotations.

Usage:
    python prepare_sroie_hf.py \
        --output-csv ~/.LINUXPRACTICE/ai-training/data/processed/sroie_field_tokens.csv
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from datasets import load_dataset
from huggingface_hub import HfApi, hf_hub_url

# darentang/sroie NER tag integer → label name used in train_lilt_kie.py
TAG_MAP = {
    0: "O",
    1: "company",   # B-COMPANY
    2: "company",   # I-COMPANY
    3: "document_date",  # B-DATE
    4: "document_date",  # I-DATE
    5: "bill_to",   # B-ADDRESS
    6: "bill_to",   # I-ADDRESS
    7: "grand_total",  # B-TOTAL
    8: "grand_total",  # I-TOTAL
}


def load_sroie() -> object:
    api = HfApi()
    files = list(api.list_repo_files(
        repo_id="darentang/sroie",
        repo_type="dataset",
        revision="refs/convert/parquet",
    ))
    urls = [
        hf_hub_url(
            "darentang/sroie", f,
            repo_type="dataset",
            revision="refs/convert/parquet",
        )
        for f in files if f.endswith(".parquet")
    ]
    if not urls:
        raise RuntimeError("No parquet files found for darentang/sroie")
    print(f"Found {len(urls)} parquet file(s)")
    return load_dataset("parquet", data_files={"train": urls})["train"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-csv",
        default=str(Path.home() / ".LINUXPRACTICE/ai-training/data/processed/sroie_field_tokens.csv"),
    )
    parser.add_argument(
        "--max-samples", type=int, default=0,
        help="Limit number of documents (0 = all)",
    )
    args = parser.parse_args()

    out_path = Path(args.output_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print("Loading darentang/sroie from HuggingFace parquet...")
    ds = load_sroie()
    n = min(len(ds), args.max_samples) if args.max_samples > 0 else len(ds)
    print(f"Processing {n} documents...")

    written = 0
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "text", "x", "y", "w", "h", "page", "label", "task_id", "filename", "image_path"
        ])
        writer.writeheader()

        for i in range(n):
            ex = ds[i]
            doc_id   = ex.get("id") or f"sroie_{i:06d}"
            task_id  = f"sroie_{doc_id}"
            words    = ex.get("words") or []
            bboxes   = ex.get("bboxes") or []
            ner_tags = ex.get("ner_tags") or []
            img_path = ex.get("image_path") or ""

            if not words:
                continue

            # Bboxes in darentang/sroie are pixel coords in ~1000x1000 space.
            # Normalize to 0.0–1.0 (train_lilt_kie.py converts back to 0–1000).
            for word, bbox, tag in zip(words, bboxes, ner_tags):
                word = (word or "").strip()
                if not word:
                    continue

                if len(bbox) == 4:
                    x1, y1, x2, y2 = [float(v) for v in bbox]
                else:
                    x1, y1, x2, y2 = 0.0, 0.0, 0.0, 0.0

                # Normalize assuming ~1000px coordinate space
                x      = max(0.0, min(1.0, x1 / 1000.0))
                y      = max(0.0, min(1.0, y1 / 1000.0))
                w_norm = max(0.0, min(1.0, (x2 - x1) / 1000.0))
                h_norm = max(0.0, min(1.0, (y2 - y1) / 1000.0))

                label = TAG_MAP.get(int(tag), "O")

                writer.writerow({
                    "text":       word,
                    "x":          f"{x:.6f}",
                    "y":          f"{y:.6f}",
                    "w":          f"{w_norm:.6f}",
                    "h":          f"{h_norm:.6f}",
                    "page":       "1",
                    "label":      label,
                    "task_id":    task_id,
                    "filename":   Path(img_path).name if img_path else "",
                    "image_path": img_path,
                })
                written += 1

    print(f"Wrote {written} token rows to {out_path}")
    print(f"Done. Feed this into train_lilt_kie.py with --tokens-csv {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())