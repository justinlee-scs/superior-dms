from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np


def _load_rows(path: Path) -> list[dict[str, str]]:
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [row for row in reader]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--min-rows", type=int, default=50)
    args = parser.parse_args()

    input_path = Path(args.input)
    rows = _load_rows(input_path)
    if len(rows) < args.min_rows:
        print(f"Not enough rows to train field extractor ({len(rows)} < {args.min_rows}).")
        return 0

    texts = [row["text"] or "" for row in rows]
    labels = [row["label"] or "O" for row in rows]
    numeric = np.array(
        [
            [
                float(row["x"] or 0),
                float(row["y"] or 0),
                float(row["w"] or 0),
                float(row["h"] or 0),
                float(row["page"] or 1),
            ]
            for row in rows
        ],
        dtype=float,
    )

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.multiclass import OneVsRestClassifier
        from sklearn.preprocessing import StandardScaler
    except Exception as exc:
        raise SystemExit(
            "scikit-learn is required to train the field extractor. "
            "Install it in your active environment (e.g., pip install scikit-learn)."
        ) from exc

    import scipy.sparse
    import joblib

    vectorizer = TfidfVectorizer(min_df=2, ngram_range=(1, 2), max_features=50000)
    text_vec = vectorizer.fit_transform(texts)

    scaler = StandardScaler(with_mean=False)
    num_vec = scaler.fit_transform(numeric)

    features = scipy.sparse.hstack([text_vec, num_vec])

    base = LogisticRegression(max_iter=1000, solver="liblinear")
    model = OneVsRestClassifier(base)
    model.fit(features, labels)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    bundle = {
        "vectorizer": vectorizer,
        "scaler": scaler,
        "model": model,
        "labels": model.classes_,
    }
    joblib.dump(bundle, output_path)
    print(f"Saved field extractor model to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
