#!/usr/bin/env python3
"""
Evaluate a LayoutLMv3 KIE model against PDFs or images.

Usage:
    python scripts/eval_kie.py \
        --docs eval-docs \
        --limit 10
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch
import pytesseract
from PIL import Image
from transformers import (
    LayoutLMv3ForTokenClassification,
    LayoutLMv3TokenizerFast,
)

sys.path.insert(0, str(Path.home() / ".LINUXPRACTICE/dms"))

from app.services.extraction.opencv_preprocess import (
    preprocess_pil_image,
)
from app.services.extraction.pdf import pdf_to_images


MODEL_PATH = (
    Path.home()
    / ".LINUXPRACTICE/ai-training/models/layoutlmv3_kie_v4"
)


def load_model():
    print(f"Loading model from {MODEL_PATH}...")

    tokenizer = LayoutLMv3TokenizerFast.from_pretrained(
        str(MODEL_PATH)
    )
    model = LayoutLMv3ForTokenClassification.from_pretrained(
        str(MODEL_PATH)
    )
    model.eval()

    label_map_path = MODEL_PATH / "label_map.json"

    if label_map_path.exists():
        data = json.loads(
            label_map_path.read_text(encoding="utf-8")
        )
        id2label = {
            int(key): value
            for key, value in data["id2label"].items()
        }
    else:
        id2label = {
            int(key): value
            for key, value in model.config.id2label.items()
        }

    return tokenizer, model, id2label


def pdf_to_image(path: Path) -> Image.Image | None:
    try:
        with path.open("rb") as f:
            pages = pdf_to_images(f.read())

        return pages[0].convert("RGB") if pages else None

    except Exception as exc:
        print(f"  PDF conversion failed: {exc}")
        return None


def load_image(path: Path) -> Image.Image | None:
    if path.suffix.lower() == ".pdf":
        return pdf_to_image(path)

    try:
        return Image.open(path).convert("RGB")
    except Exception as exc:
        print(f"  Image load failed: {exc}")
        return None


def ocr(
    image: Image.Image,
) -> tuple[list[str], list[list[int]]]:
    """
    Use the same preprocessing as the training-data generator.
    Return words and boxes normalized to 0-1000.
    """
    try:
        processed = preprocess_pil_image(image)
    except Exception:
        processed = image.convert("RGB")

    processed = processed.convert("RGB")
    width, height = processed.size

    data = pytesseract.image_to_data(
        processed,
        output_type=pytesseract.Output.DICT,
    )

    words: list[str] = []
    boxes: list[list[int]] = []

    for index, text in enumerate(data.get("text", [])):
        word = (text or "").strip()

        if not word:
            continue

        try:
            confidence = float(
                data.get("conf", ["-1"])[index]
            )
        except Exception:
            confidence = -1.0

        if confidence < 0:
            continue

        x = float(data["left"][index])
        y = float(data["top"][index])
        box_width = float(data["width"][index])
        box_height = float(data["height"][index])

        x0 = max(0, min(1000, int(x / width * 1000)))
        y0 = max(0, min(1000, int(y / height * 1000)))
        x1 = max(
            0,
            min(1000, int((x + box_width) / width * 1000)),
        )
        y1 = max(
            0,
            min(1000, int((y + box_height) / height * 1000)),
        )

        words.append(word)
        boxes.append([x0, y0, x1, y1])

    return words, boxes


def extract_fields(
    image: Image.Image,
    tokenizer,
    model,
    id2label: dict[int, str],
) -> dict[str, list[str]]:
    words, boxes = ocr(image)

    if not words:
        return {"error": ["No text detected"]}

    if len(words) > 512:
        print(
            f"  WARNING: {len(words)} OCR words; "
            "only the first 512 will be evaluated"
        )

    encoding = tokenizer(
        words,
        boxes=boxes,
        max_length=512,
        padding="max_length",
        truncation=True,
        return_tensors="pt",
    )

    with torch.no_grad():
        logits = model(**encoding).logits[0]

    probabilities = torch.softmax(logits, dim=-1)
    pred_ids = torch.argmax(logits, dim=-1).tolist()
    confidences = probabilities.max(dim=-1).values.tolist()
    word_ids = encoding.word_ids(batch_index=0)

    fields: dict[str, list[str]] = {}
    current_label: str | None = None
    current_words: list[str] = []

    def finish_span() -> None:
        nonlocal current_label, current_words

        if current_label and current_words:
            value = " ".join(current_words).strip()

            if value:
                fields.setdefault(
                    current_label,
                    [],
                ).append(value)

        current_label = None
        current_words = []

    for token_index, word_id in enumerate(word_ids):
        if word_id is None:
            continue

        # Process only the first subword for each OCR word.
        if (
            token_index > 0
            and word_ids[token_index - 1] == word_id
        ):
            continue

        label = id2label.get(pred_ids[token_index], "O")

        if confidences[token_index] < 0.50:
            label = "O"

        word = words[word_id]

        if label == "O":
            finish_span()
            continue

        if label.startswith("B-"):
            finish_span()
            current_label = label[2:]
            current_words = [word]
            continue

        if label.startswith("I-"):
            field_name = label[2:]

            if current_label == field_name:
                current_words.append(word)
            else:
                finish_span()
                current_label = field_name
                current_words = [word]

            continue

        # Support plain labels such as "company".
        if current_label == label:
            current_words.append(word)
        else:
            finish_span()
            current_label = label
            current_words = [word]

    finish_span()

    return fields or {"note": ["No fields extracted"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--docs",
        required=True,
        help="Folder containing PDFs or images",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of documents",
    )
    args = parser.parse_args()

    docs_dir = Path(args.docs)

    if not docs_dir.exists():
        print(f"Folder not found: {docs_dir}")
        return 1

    tokenizer, model, id2label = load_model()

    print(f"Labels: {list(id2label.values())}\n")

    extensions = {
        ".pdf",
        ".png",
        ".jpg",
        ".jpeg",
        ".tiff",
    }

    files = sorted(
        path
        for path in docs_dir.iterdir()
        if path.suffix.lower() in extensions
    )

    files = files[:args.limit]

    if not files:
        print(f"No supported files found in {docs_dir}")
        return 1

    print(f"Evaluating {len(files)} documents...\n")
    print("=" * 70)

    for path in files:
        print(f"\nFile: {path.name}")

        image = load_image(path)

        if image is None:
            print("  SKIP — could not load")
            continue

        fields = extract_fields(
            image,
            tokenizer,
            model,
            id2label,
        )

        for field, values in fields.items():
            for value in values:
                print(f"  {field:<20} {value}")

        print("-" * 70)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())