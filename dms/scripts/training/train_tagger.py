from __future__ import annotations

import argparse
import csv
import joblib

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    texts: list[str] = []
    labels: list[list[str]] = []
    tag_set: set[str] = set()

    with open(args.input, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = (row.get("text") or "").strip()
            tags_raw = (row.get("tags") or "").strip()
            if not text or not tags_raw:
                continue
            tags = [t for t in (tag.strip() for tag in tags_raw.split(",")) if t]
            if not tags:
                continue
            texts.append(text)
            labels.append(tags)
            tag_set.update(tags)

    if not texts:
        raise SystemExit("No training rows found.")

    tag_list = sorted(tag_set)
    tag_index = {tag: i for i, tag in enumerate(tag_list)}

    y = []
    for tags in labels:
        row = [0] * len(tag_list)
        for tag in tags:
            row[tag_index[tag]] = 1
        y.append(row)

    vectorizer = TfidfVectorizer(max_features=8000, ngram_range=(1, 2))
    X = vectorizer.fit_transform(texts)
    classifier = OneVsRestClassifier(LogisticRegression(max_iter=1000))
    classifier.fit(X, y)

    joblib.dump(
        {
            "vectorizer": vectorizer,
            "model": classifier,
            "labels": tag_list,
        },
        args.output,
    )
    print(f"Saved model to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
