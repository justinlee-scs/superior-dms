#!/usr/bin/env python3
"""
Run a LayoutLMv3 KIE model against PDFs or images and create a JSON file
containing model guesses for manual review.

Usage:
    python scripts/prefill_annotations.py \
        --docs eval-docs \
        --output data/processed/annotations.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch
from PIL import Image
from transformers import (
    LayoutLMv3ForTokenClassification,
    LayoutLMv3TokenizerFast,
)

sys.path.insert(0, str(Path.home() / ".LINUXPRACTICE/dms"))

from app.services.extraction.opencv_preprocess import preprocess_pil_image
from app.services.extraction.pdf import pdf_to_images


MODEL_PATH = (
    Path.home()
    / ".LINUXPRACTICE/ai-training/models/layoutlmv3_kie_v4"
)

FIELDS = [
    "company",
    "invoice_number",
    "document_date",
    "due_date",
    "grand_total",
    "bill_to",
    "billing_address",
    "shipping_address",
    "document_type",
    "account_number",
    "gst_number",
    "pst_number",
]


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
        data = json.loads(label_map_path.read_text(encoding="utf-8"))
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


def load_image(path: Path) -> Image.Image | None:
    try:
        if path.suffix.lower() == ".pdf":
            with path.open("rb") as f:
                pages = pdf_to_images(f.read())

            if not pages:
                return None

            return pages[0].convert("RGB")

        return Image.open(path).convert("RGB")

    except Exception as exc:
        print(f"  Could not load {path.name}: {exc}")
        return None


def ocr(image: Image.Image) -> tuple[list[str], list[list[int]]]:
    """
    Run the same OCR preprocessing used by the training-data generator.
    Returns words and boxes normalized to 0-1000.
    """
    import pytesseract

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
            confidence = float(data.get("conf", ["-1"])[index])
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
) -> dict[str, str]:
    words, boxes = ocr(image)

    if not words:
        return {}

    if len(words) > 512:
        print(
            f"  WARNING: {len(words)} OCR words; "
            "only the first 512 will be processed"
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
                fields.setdefault(current_label, []).append(value)

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

        # Suppress low-confidence guesses in the prefill file.
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

    # Keep the first value for each field because the annotation schema
    # currently stores one value per field.
    return {
        field: values[0]
        for field, values in fields.items()
        if values
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs", default="eval-docs")
    parser.add_argument(
        "--output",
        default="data/processed/annotations.json",
    )
    args = parser.parse_args()

    docs_dir = Path(args.docs)
    output_path = Path(args.output)

    if not docs_dir.exists():
        print(f"Folder not found: {docs_dir}")
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)

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

    print(f"Found {len(files)} documents")

    tokenizer, model, id2label = load_model()
    annotations = []

    for path in files:
        print(f"Processing {path.name}...")

        image = load_image(path)

        if image is None:
            annotations.append(
                {
                    "image_path": str(path),
                    "image_file": path.name,
                    **{field: "" for field in FIELDS},
                }
            )
            continue

        guesses = extract_fields(
            image,
            tokenizer,
            model,
            id2label,
        )

        annotations.append(
            {
                "image_path": str(path),
                "image_file": path.name,
                **{
                    field: guesses.get(field, "")
                    for field in FIELDS
                },
            }
        )

    output_path.write_text(
        json.dumps(annotations, indent=2),
        encoding="utf-8",
    )

    print(f"\nDone. Review and correct: {output_path}")
    print("Then run:")
    print(
        "  python scripts/"
        "prepare_sroie_invoice_warmstart_json.py \\"
    )
    print(f"      --input-json {output_path} \\")
    print(
        "      --output-dir "
        "data/processed/dms_annotated \\"
    )
    print(f"      --image-root {docs_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())