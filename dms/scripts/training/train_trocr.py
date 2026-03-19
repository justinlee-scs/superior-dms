from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image
from torch.utils.data import Dataset
import torch
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from transformers import Seq2SeqTrainer, Seq2SeqTrainingArguments


class TrOCRDataset(Dataset):
    def __init__(self, rows: list[dict[str, str]], processor: TrOCRProcessor, max_length: int):
        self.rows = rows
        self.processor = processor
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, idx: int):
        row = self.rows[idx]
        image = Image.open(row["image_path"]).convert("RGB")
        pixel_values = self.processor(images=image, return_tensors="pt").pixel_values.squeeze(0)
        labels = self.processor.tokenizer(
            row["text"],
            padding="max_length",
            max_length=self.max_length,
            truncation=True,
            return_tensors="pt",
        ).input_ids.squeeze(0)
        labels[labels == self.processor.tokenizer.pad_token_id] = -100
        return {"pixel_values": pixel_values, "labels": labels}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", default="microsoft/trocr-base-handwritten")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--max-length", type=int, default=64)
    args = parser.parse_args()

    rows: list[dict[str, str]] = []
    with open(args.input, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            if Path(row["image_path"]).exists() and row.get("text"):
                rows.append(row)

    if not rows:
        raise SystemExit("No training rows found.")

    processor = TrOCRProcessor.from_pretrained(args.model)
    model = VisionEncoderDecoderModel.from_pretrained(args.model)

    dataset = TrOCRDataset(rows, processor, max_length=args.max_length)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    training_args = Seq2SeqTrainingArguments(
        output_dir=str(output_dir),
        per_device_train_batch_size=args.batch_size,
        num_train_epochs=args.epochs,
        save_total_limit=1,
        predict_with_generate=False,
        fp16=False,
        logging_steps=10,
        remove_unused_columns=False,
    )

    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        tokenizer=processor,
    )

    trainer.train()
    model.save_pretrained(output_dir)
    processor.save_pretrained(output_dir)
    print(f"Saved TrOCR model to {output_dir}")
    return 0


if __name__ == "__main__":
    torch.set_num_threads(2)
    raise SystemExit(main())
