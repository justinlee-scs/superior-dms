from __future__ import annotations

import argparse
import csv
from pathlib import Path

import torch
from PIL import Image
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score


class SimpleCNN(torch.nn.Module):
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
    model = SimpleCNN()
    state = torch.load(path, map_location="cpu")
    if isinstance(state, dict) and "state_dict" in state:
        state = state["state_dict"]
    model.load_state_dict(state)
    model.eval()
    return model


def _preprocess(path: str, image_size: int) -> torch.Tensor:
    image = Image.open(path).convert("RGB").resize((image_size, image_size))
    data = torch.tensor(list(image.getdata()), dtype=torch.float32)
    data = data.view(image_size, image_size, 3).permute(2, 0, 1)
    data = data / 255.0
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--image-size", type=int, default=224)
    args = parser.parse_args()

    rows: list[tuple[str, int]] = []
    with open(args.input, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            path = (row.get("image_path") or "").strip()
            label = (row.get("label") or "").strip().lower()
            if not path or not Path(path).exists():
                continue
            if label in {"handwritten", "mixed"}:
                rows.append((path, 1))
            elif label in {"printed"}:
                rows.append((path, 0))

    if not rows:
        raise SystemExit("No evaluation rows found.")

    model = _load_model(args.model)
    preds: list[int] = []
    targets: list[int] = []
    for path, label in rows:
        tensor = _preprocess(path, args.image_size).unsqueeze(0)
        with torch.no_grad():
            logit = model(tensor)
            prob = torch.sigmoid(logit).item()
        preds.append(1 if prob >= args.threshold else 0)
        targets.append(label)

    print(f"accuracy: {accuracy_score(targets, preds):.4f}")
    print(f"precision: {precision_score(targets, preds):.4f}")
    print(f"recall: {recall_score(targets, preds):.4f}")
    print(f"f1: {f1_score(targets, preds):.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
