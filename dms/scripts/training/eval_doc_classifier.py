from __future__ import annotations

import argparse
import csv
import joblib

from sklearn.metrics import accuracy_score, classification_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--model", required=True)
    args = parser.parse_args()

    bundle = joblib.load(args.model)
    vectorizer = bundle["vectorizer"]
    model = bundle["model"]

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
        raise SystemExit("No evaluation rows found.")

    X = vectorizer.transform(texts)
    preds = model.predict(X)
    print(f"accuracy: {accuracy_score(labels, preds):.4f}")
    print(classification_report(labels, preds))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
