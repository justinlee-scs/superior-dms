from __future__ import annotations

import argparse
import csv
from pathlib import Path

import torch
from torch.utils.data import Dataset, DataLoader
from PIL import Image


class HandwritingDataset(Dataset):
    def __init__(self, rows: list[tuple[str, int]], image_size: int):
        self.rows = rows
        self.image_size = image_size

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, idx: int):
        path, label = self.rows[idx]
        image = Image.open(path).convert("RGB").resize((self.image_size, self.image_size))
        data = torch.tensor(list(image.getdata()), dtype=torch.float32)
        data = data.view(self.image_size, self.image_size, 3).permute(2, 0, 1)
        data = data / 255.0
        return data, torch.tensor([label], dtype=torch.float32)


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=8)
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
        raise SystemExit("No training rows found.")

    dataset = HandwritingDataset(rows, image_size=args.image_size)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True)

    model = SimpleCNN()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = torch.nn.BCEWithLogitsLoss()

    model.train()
    for epoch in range(args.epochs):
        total_loss = 0.0
        for batch_x, batch_y in loader:
            optimizer.zero_grad()
            logits = model(batch_x)
            loss = loss_fn(logits, batch_y)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        print(f"epoch {epoch + 1}: loss={total_loss:.4f}")

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), args.output)
    print(f"Saved model to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
