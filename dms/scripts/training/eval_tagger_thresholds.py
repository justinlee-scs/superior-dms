from __future__ import annotations

import argparse
import csv
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import precision_score, recall_score, f1_score


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--min-threshold", type=float, default=0.50)
    parser.add_argument("--max-threshold", type=float, default=0.99)
    parser.add_argument("--step", type=float, default=0.01)
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
    if not hasattr(model, "predict_proba"):
        raise SystemExit("Model does not support predict_proba; cannot sweep thresholds.")

    probs = model.predict_proba(X)
    y_true = np.array(targets)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["tag", "threshold", "precision", "recall", "f1", "support", "predicted"]
        )
        threshold = args.min_threshold
        while threshold <= args.max_threshold + 1e-9:
            y_pred = (probs >= threshold).astype(int)
            for idx, label in enumerate(labels):
                col_true = y_true[:, idx]
                col_pred = y_pred[:, idx]
                support = int(col_true.sum())
                predicted = int(col_pred.sum())
                if support == 0 and predicted == 0:
                    precision = 1.0
                    recall = 1.0
                    f1 = 1.0
                else:
                    precision = precision_score(col_true, col_pred, zero_division=1)
                    recall = recall_score(col_true, col_pred, zero_division=0)
                    f1 = f1_score(col_true, col_pred, zero_division=0)
                writer.writerow(
                    [
                        label,
                        f"{threshold:.2f}",
                        f"{precision:.4f}",
                        f"{recall:.4f}",
                        f"{f1:.4f}",
                        support,
                        predicted,
                    ]
                )
            threshold += args.step

    print(f"Saved threshold sweep to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
