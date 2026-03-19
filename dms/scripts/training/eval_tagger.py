from __future__ import annotations

import argparse
import csv
import joblib

import numpy as np
from sklearn.metrics import f1_score, precision_score, recall_score


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--threshold", type=float, default=0.5)
    args = parser.parse_args()

    bundle = joblib.load(args.model)
    vectorizer = bundle["vectorizer"]
    model = bundle["model"]
    labels = bundle["labels"]

    texts: list[str] = []
    targets: list[list[int]] = []
    with open(args.input, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = (row.get("text") or "").strip()
            tags_raw = (row.get("tags") or "").strip()
            if not text or not tags_raw:
                continue
            tags = {t.strip() for t in tags_raw.split(",") if t.strip()}
            row_vec = [1 if label in tags else 0 for label in labels]
            texts.append(text)
            targets.append(row_vec)

    if not texts:
        raise SystemExit("No evaluation rows found.")

    X = vectorizer.transform(texts)
    if hasattr(model, "predict_proba"):
        probs = model.predict_proba(X)
        preds = (probs >= args.threshold).astype(int)
    else:
        preds = model.predict(X)

    y_true = np.array(targets)
    y_pred = np.array(preds)
    print(f"micro_f1: {f1_score(y_true, y_pred, average='micro'):.4f}")
    print(f"macro_f1: {f1_score(y_true, y_pred, average='macro'):.4f}")
    print(f"micro_precision: {precision_score(y_true, y_pred, average='micro'):.4f}")
    print(f"micro_recall: {recall_score(y_true, y_pred, average='micro'):.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
