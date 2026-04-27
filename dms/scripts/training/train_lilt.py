from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

import torch
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from transformers import LayoutLMv3ForTokenClassification, LayoutLMv3Processor


def _norm_box(x: float, y: float, w: float, h: float) -> list[int]:
    x0 = max(0, min(1000, int(round(x * 1000))))
    y0 = max(0, min(1000, int(round(y * 1000))))
    x1 = max(0, min(1000, int(round((x + w) * 1000))))
    y1 = max(0, min(1000, int(round((y + h) * 1000))))
    if x1 < x0:
        x1 = x0
    if y1 < y0:
        y1 = y0
    return [x0, y0, x1, y1]


@dataclass
class TokenRow:
    text: str
    x: float
    y: float
    w: float
    h: float
    label: str
    task_id: str
    image_path: str


def _load_rows(path: Path) -> list[TokenRow]:
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows: list[TokenRow] = []
        for r in reader:
            rows.append(
                TokenRow(
                    text=(r.get("text") or "").strip(),
                    x=float(r.get("x") or 0.0),
                    y=float(r.get("y") or 0.0),
                    w=float(r.get("w") or 0.0),
                    h=float(r.get("h") or 0.0),
                    label=(r.get("label") or "O").strip() or "O",
                    task_id=(r.get("task_id") or "").strip(),
                    image_path=(r.get("image_path") or "").strip(),
                )
            )
    return rows


def _to_bio(raw_labels: list[str]) -> list[str]:
    out: list[str] = []
    prev_entity = None
    for label in raw_labels:
        clean = label.strip()
        if not clean or clean.upper() == "O":
            out.append("O")
            prev_entity = None
            continue
        entity = clean.upper().replace(" ", "_")
        prefix = "I-" if prev_entity == entity else "B-"
        out.append(f"{prefix}{entity}")
        prev_entity = entity
    return out


def _group_sequences(rows: list[TokenRow]) -> list[dict[str, object]]:
    buckets: dict[tuple[str, str], list[TokenRow]] = {}
    for row in rows:
        if not row.text or not row.image_path:
            continue
        key = (row.task_id, row.image_path)
        buckets.setdefault(key, []).append(row)

    grouped: list[dict[str, object]] = []
    for (_, image_path), seq_rows in buckets.items():
        words = [r.text for r in seq_rows]
        boxes = [_norm_box(r.x, r.y, r.w, r.h) for r in seq_rows]
        bio = _to_bio([r.label for r in seq_rows])
        grouped.append(
            {
                "image_path": image_path,
                "words": words,
                "boxes": boxes,
                "labels": bio,
            }
        )
    return grouped


class LiLTDataset(Dataset):
    def __init__(
        self,
        records: list[dict[str, object]],
        *,
        processor: LayoutLMv3Processor,
        label2id: dict[str, int],
        max_length: int,
    ):
        self.records = records
        self.processor = processor
        self.label2id = label2id
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        rec = self.records[idx]
        image = Image.open(str(rec["image_path"])).convert("RGB")
        words = rec["words"]
        boxes = rec["boxes"]
        labels = [self.label2id[l] for l in rec["labels"]]

        enc = self.processor(
            image,
            words,
            boxes=boxes,
            word_labels=labels,
            truncation=True,
            padding="max_length",
            max_length=self.max_length,
            return_tensors="pt",
        )
        return {k: v.squeeze(0) for k, v in enc.items()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="field_tokens.csv")
    parser.add_argument("--output", required=True, help="Output model directory")
    parser.add_argument("--base-model", default="microsoft/layoutlmv3-base")
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--lr", type=float, default=3e-5)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--min-sequences", type=int, default=10)
    args = parser.parse_args()

    rows = _load_rows(Path(args.input))
    records = _group_sequences(rows)
    if len(records) < args.min_sequences:
        print(
            f"Not enough labeled sequences to train LiLT ({len(records)} < {args.min_sequences})."
        )
        return 0

    label_set: set[str] = {"O"}
    for rec in records:
        label_set.update(rec["labels"])
    labels = sorted(label_set)
    label2id = {l: i for i, l in enumerate(labels)}
    id2label = {i: l for l, i in label2id.items()}

    processor = LayoutLMv3Processor.from_pretrained(args.base_model, apply_ocr=False)
    model = LayoutLMv3ForTokenClassification.from_pretrained(
        args.base_model,
        num_labels=len(labels),
        id2label=id2label,
        label2id=label2id,
    )

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    model.train()

    ds = LiLTDataset(
        records,
        processor=processor,
        label2id=label2id,
        max_length=args.max_length,
    )
    dl = DataLoader(ds, batch_size=args.batch_size, shuffle=True)
    optim = torch.optim.AdamW(model.parameters(), lr=args.lr)

    for epoch in range(args.epochs):
        total_loss = 0.0
        steps = 0
        for batch in dl:
            batch = {k: v.to(device) for k, v in batch.items()}
            out = model(**batch)
            loss = out.loss
            loss.backward()
            optim.step()
            optim.zero_grad()
            total_loss += float(loss.item())
            steps += 1
        avg = total_loss / steps if steps else 0.0
        print(f"epoch={epoch + 1} avg_loss={avg:.6f}")

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(out_dir)
    processor.save_pretrained(out_dir)
    print(f"Saved LiLT model to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
