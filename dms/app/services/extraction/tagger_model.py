from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class TaggerModel:
    vectorizer: Any
    model: Any
    labels: list[str]

    def predict(self, text: str, *, threshold: float = 0.5) -> list[str]:
        features = self.vectorizer.transform([text or ""])
        if hasattr(self.model, "predict_proba"):
            probs = self.model.predict_proba(features)
            if isinstance(probs, list):
                probs = probs[0]
            return [
                label
                for label, prob in zip(self.labels, probs)
                if prob >= threshold
            ]
        outputs = self.model.predict(features)
        if outputs is None or not len(outputs):
            return []
        row = outputs[0]
        return [label for label, value in zip(self.labels, row) if value]
