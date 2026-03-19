from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

import torch
from PIL import Image


@dataclass
class HandwritingClassifier:
    model: torch.nn.Module
    threshold: float = 0.5
    image_size: int = 224

    def _preprocess(self, image: Image.Image) -> torch.Tensor:
        image = image.convert("RGB").resize((self.image_size, self.image_size))
        data = torch.tensor(list(image.getdata()), dtype=torch.float32)
        data = data.view(self.image_size, self.image_size, 3).permute(2, 0, 1)
        data = data / 255.0
        return data

    def predict_scores(self, images: list[Image.Image]) -> list[float]:
        if not images:
            return []
        batch = torch.stack([self._preprocess(img) for img in images])
        with torch.no_grad():
            logits = self.model(batch)
            probs = torch.sigmoid(logits).squeeze(-1)
        return probs.cpu().tolist()

    def is_handwritten(self, images: list[Image.Image]) -> bool:
        scores = self.predict_scores(images[:3])
        if not scores:
            return False
        avg = sum(scores) / len(scores)
        return avg >= self.threshold


class _SimpleCNN(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.features = torch.nn.Sequential(
            torch.nn.Conv2d(3, 16, kernel_size=3, stride=2, padding=1),
            torch.nn.ReLU(inplace=True),
            torch.nn.Conv2d(16, 32, kernel_size=3, stride=2, padding=1),
            torch.nn.ReLU(inplace=True),
            torch.nn.Conv2d(32, 64, kernel_size=3, stride=2, padding=1),
            torch.nn.ReLU(inplace=True),
            torch.nn.AdaptiveAvgPool2d(1),
        )
        self.classifier = torch.nn.Linear(64, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = x.view(x.size(0), -1)
        return self.classifier(x)


def _load_model(path: str) -> torch.nn.Module:
    if path.endswith(".pt") or path.endswith(".pth"):
        model = _SimpleCNN()
        state = torch.load(path, map_location="cpu")
        if isinstance(state, dict) and "state_dict" in state:
            state = state["state_dict"]
        model.load_state_dict(state)
        model.eval()
        return model
    if path.endswith(".jit"):
        model = torch.jit.load(path, map_location="cpu")
        model.eval()
        return model
    raise ValueError("Unsupported handwriting model format. Use .pt/.pth or .jit")


@lru_cache(maxsize=1)
def get_handwriting_classifier() -> Optional[HandwritingClassifier]:
    path = os.getenv("HANDWRITING_MODEL_PATH", "").strip()
    if not path:
        return None
    model = _load_model(path)
    threshold = float(os.getenv("HANDWRITING_THRESHOLD", "0.5"))
    image_size = int(os.getenv("HANDWRITING_IMAGE_SIZE", "224"))
    return HandwritingClassifier(model=model, threshold=threshold, image_size=image_size)
