#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import List, Tuple

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


def load_csv(path: Path) -> List[Tuple[str, str]]:
    rows: List[Tuple[str, str]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            text = (row.get("text") or "").strip()
            label = (row.get("label") or "").strip()
            if text and label:
                rows.append((text, label))
    return rows


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dms-csv", required=True, help="Path to DMS doc_class.csv")
    p.add_argument("--rvl-csv", default="", help="Optional RVL-derived text,label CSV")
    p.add_argument("--output", required=True, help="Output .joblib path")
    p.add_argument("--max-features", type=int, default=50000)
    p.add_argument("--c", type=float, default=4.0)
    args = p.parse_args()

    dms_rows = load_csv(Path(args.dms_csv))
    if not dms_rows:
        raise SystemExit("No valid rows in DMS CSV.")

    merged = list(dms_rows)
    if args.rvl_csv:
        merged.extend(load_csv(Path(args.rvl_csv)))

    texts = [t for t, _ in merged]
    labels = [y for _, y in merged]

    model = Pipeline(
        steps=[
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), max_features=args.max_features)),
            ("clf", LogisticRegression(max_iter=2000, C=args.c, n_jobs=-1)),
        ]
    )
    model.fit(texts, labels)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "labels": sorted(set(labels))}, out)
    print(f"Saved merged doc classifier: {out}")
    print(f"Rows used: {len(merged)} (DMS={len(dms_rows)}, RVL_extra={len(merged)-len(dms_rows)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
