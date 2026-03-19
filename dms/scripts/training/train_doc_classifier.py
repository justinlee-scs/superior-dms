from __future__ import annotations

import argparse
import csv
import joblib

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    texts: list[str] = []
    labels: list[str] = []
    with open(args.input, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = (row.get("text") or "").strip()
            label = (row.get("label") or "").strip()
            if text and label:
                texts.append(text)
                labels.append(label)

    if not texts:
        raise SystemExit("No training rows found.")

    vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
    X = vectorizer.fit_transform(texts)
    model = LogisticRegression(max_iter=1000)
    model.fit(X, labels)

    joblib.dump(
        {
            "vectorizer": vectorizer,
            "model": model,
            "labels": sorted(set(labels)),
        },
        args.output,
    )
    print(f"Saved model to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
