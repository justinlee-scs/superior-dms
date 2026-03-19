from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image
import torch
from transformers import TrOCRProcessor, VisionEncoderDecoderModel


def _edit_distance(a: list[str], b: list[str]) -> int:
    if not a:
        return len(b)
    if not b:
        return len(a)
    dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1):
        dp[i][0] = i
    for j in range(len(b) + 1):
        dp[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,
                dp[i][j - 1] + 1,
                dp[i - 1][j - 1] + cost,
            )
    return dp[-1][-1]


def _wer(ref: str, hyp: str) -> float:
    r = ref.split()
    h = hyp.split()
    if not r:
        return 1.0 if h else 0.0
    return _edit_distance(r, h) / len(r)


def _cer(ref: str, hyp: str) -> float:
    r = list(ref)
    h = list(hyp)
    if not r:
        return 1.0 if h else 0.0
    return _edit_distance(r, h) / len(r)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--max-samples", type=int, default=50)
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
        raise SystemExit("No evaluation rows found.")

    processor = TrOCRProcessor.from_pretrained(args.model)
    model = VisionEncoderDecoderModel.from_pretrained(args.model)

    total_cer = 0.0
    total_wer = 0.0
    count = 0
    for row in rows[: args.max_samples]:
        image = Image.open(row["image_path"]).convert("RGB")
        pixel_values = processor(images=image, return_tensors="pt").pixel_values
        with torch.no_grad():
            generated_ids = model.generate(pixel_values)
        pred = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        ref = row["text"]
        total_cer += _cer(ref, pred)
        total_wer += _wer(ref, pred)
        count += 1

    print(f"samples: {count}")
    print(f"cer: {total_cer / count:.4f}")
    print(f"wer: {total_wer / count:.4f}")
    return 0


if __name__ == "__main__":
    torch.set_num_threads(2)
    raise SystemExit(main())
