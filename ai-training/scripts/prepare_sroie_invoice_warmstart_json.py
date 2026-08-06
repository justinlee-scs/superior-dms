#!/usr/bin/env python3
"""
Convert reviewed JSON annotations into field_tokens.csv.

Usage:
    python scripts/prepare_sroie_invoice_warmstart_json.py \
        --input-json data/processed/annotations.json \
        --output-dir data/processed/dms_annotated \
        --image-root eval-docs
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from PIL import Image

try:
    import pytesseract
    from pytesseract import Output
except Exception as exc:
    raise SystemExit("pytesseract is required") from exc

import sys

sys.path.insert(0, str(Path.home() / ".LINUXPRACTICE/dms"))

from app.services.extraction.opencv_preprocess import (
    preprocess_pil_image,
)


FIELDS = [
    "company",
    "document_date",
    "due_date",
    "grand_total",
    "bill_to",
    "invoice_number",
    "billing_address",
    "shipping_address",
    "document_type",
    "account_number",
    "gst_number",
    "pst_number",
]


@dataclass(frozen=True)
class Token:
    text: str
    x: float
    y: float
    w: float
    h: float
    page: int = 1


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def norm_compare(text: str) -> str:
    return re.sub(
        r"[^a-z0-9]+",
        "",
        (text or "").lower(),
    )


def parse_date(value: str) -> str:
    value = clean(value)

    if not value:
        return ""

    patterns = (
        r"\b(\d{4})-(\d{2})-(\d{2})\b",
        r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b",
        r"\b(\d{1,2})-(\d{1,2})-(\d{2,4})\b",
    )

    for pattern in patterns:
        match = re.search(pattern, value)

        if not match:
            continue

        if len(match.group(1)) == 4:
            try:
                return date(
                    int(match.group(1)),
                    int(match.group(2)),
                    int(match.group(3)),
                ).isoformat()
            except ValueError:
                return ""

        month = int(match.group(1))
        day = int(match.group(2))
        year = int(match.group(3))

        if year < 100:
            year += 2000

        try:
            return date(year, month, day).isoformat()
        except ValueError:
            return ""

    return ""


def normalize_money(value: str) -> str:
    cleaned = clean(value).replace(",", "")
    match = re.search(
        r"(\d+(?:\.\d{1,2})?)",
        cleaned,
    )
    return match.group(1) if match else ""


def load_image(path: Path) -> Image.Image:
    if path.suffix.lower() == ".pdf":
        from app.services.extraction.pdf import pdf_to_images

        with path.open("rb") as f:
            pages = pdf_to_images(f.read())

        if not pages:
            raise ValueError(f"Could not render PDF: {path}")

        return pages[0].convert("RGB")

    return Image.open(path).convert("RGB")


def ocr_tokens(image: Image.Image) -> list[Token]:
    try:
        processed = preprocess_pil_image(image)
    except Exception:
        processed = image.convert("RGB")

    processed = processed.convert("RGB")
    data = pytesseract.image_to_data(
        processed,
        output_type=Output.DICT,
    )

    width, height = processed.size
    tokens: list[Token] = []

    for index, text in enumerate(data.get("text", [])):
        cleaned = clean(str(text))

        if not cleaned:
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

        tokens.append(
            Token(
                text=cleaned,
                x=x / width if width else 0.0,
                y=y / height if height else 0.0,
                w=box_width / width if width else 0.0,
                h=box_height / height if height else 0.0,
            )
        )

    return tokens


def find_span(
    tokens: list[Token],
    value: str,
) -> tuple[int, int] | None:
    """
    Find an exact contiguous sequence of OCR tokens.

    This intentionally does not match words with arbitrary OCR tokens
    between them, because that would create noisy labels.
    """
    parts = [
        norm_compare(part)
        for part in re.split(r"\s+", value)
        if norm_compare(part)
    ]

    if not parts:
        return None

    normalized = [
        norm_compare(token.text)
        for token in tokens
    ]

    for start in range(len(normalized) - len(parts) + 1):
        candidate = normalized[
            start:start + len(parts)
        ]

        if candidate == parts:
            return start, start + len(parts)

    # Conservative single-token fallback.
    for part in parts:
        if len(part) < 3:
            continue

        for index, token_norm in enumerate(normalized):
            if token_norm == part:
                return index, index + 1

    return None


def annotation_value(
    annotations: dict[str, str],
    field: str,
) -> str:
    """
    Support both the new snake_case names and the old names with spaces.
    """
    aliases = {
        "billing_address": "billing address",
        "shipping_address": "shipping address",
    }

    value = annotations.get(field)

    if value:
        return clean(value)

    old_name = aliases.get(field, "")
    return clean(annotations.get(old_name, ""))


def label_tokens(
    tokens: list[Token],
    annotations: dict[str, str],
) -> list[str]:
    labels = ["O"] * len(tokens)
    failures: list[str] = []

    def apply(field: str) -> None:
        value = annotation_value(annotations, field)

        if not value:
            return

        span = find_span(tokens, value)

        if span is None:
            failures.append(f"{field}={value!r}")
            return

        start, end = span

        for index in range(
            start,
            min(end, len(labels)),
        ):
            labels[index] = field

    for field in FIELDS:
        apply(field)

    if failures:
        print(
            "  Could not align: "
            + ", ".join(failures)
        )

    return labels


def build_tags(
    annotations: dict[str, str],
) -> list[str]:
    tags: list[str] = []

    for field in FIELDS:
        value = annotation_value(annotations, field)

        if not value:
            continue

        if field in {"document_date", "due_date"}:
            normalized = parse_date(value)
            value = normalized or value

        if field == "grand_total":
            normalized = normalize_money(value)
            value = normalized or value

        tags.append(f"{field}:{value}")

    return sorted(set(tags))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-json", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--image-root", default="")
    args = parser.parse_args()

    input_json = Path(args.input_json)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    image_root = (
        Path(args.image_root).resolve()
        if args.image_root
        else None
    )

    rows = json.loads(
        input_json.read_text(encoding="utf-8")
    )

    tags_rows: list[tuple[str, str]] = []
    token_rows: list[list[str]] = []

    for document_index, row in enumerate(rows):
        image_ref = clean(
            row.get("image_path")
            or row.get("image_file")
            or ""
        )

        if not image_ref:
            print(
                f"Skipping row {document_index}: "
                "no image path"
            )
            continue

        image_path = Path(image_ref)

        if not image_path.exists() and image_root:
            image_path = image_root / Path(image_ref).name

        if not image_path.exists():
            print(f"Skipping missing file: {image_ref}")
            continue

        annotations = {
            field: row.get(field) or ""
            for field in FIELDS
        }

        # Support old JSON keys with spaces.
        annotations["billing address"] = (
            row.get("billing address") or ""
        )
        annotations["shipping address"] = (
            row.get("shipping address") or ""
        )

        try:
            image = load_image(image_path)
            tokens = ocr_tokens(image)
        except Exception as exc:
            print(
                f"Skipping {image_path.name}: {exc}"
            )
            continue

        if len(tokens) > 512:
            print(
                f"WARNING {image_path.name}: "
                f"{len(tokens)} OCR tokens; "
                "training will truncate to 512"
            )

        labels = label_tokens(tokens, annotations)
        tags = build_tags(annotations)

        text = " ".join(
            token.text for token in tokens
        ).strip()

        if text and tags:
            tags_rows.append(
                (text, ",".join(tags))
            )

        task_id = f"dms_{document_index:06d}"

        for token, label in zip(tokens, labels):
            token_rows.append(
                [
                    token.text,
                    f"{token.x:.6f}",
                    f"{token.y:.6f}",
                    f"{token.w:.6f}",
                    f"{token.h:.6f}",
                    str(token.page),
                    label,
                    task_id,
                    image_path.name,
                    str(image_path),
                ]
            )

    tags_path = output_dir / "tags.csv"
    tokens_path = output_dir / "field_tokens.csv"

    with tags_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as f:
        writer = csv.writer(f)
        writer.writerow(["text", "tags"])
        writer.writerows(tags_rows)

    with tokens_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "text",
                "x",
                "y",
                "w",
                "h",
                "page",
                "label",
                "task_id",
                "filename",
                "image_path",
            ]
        )
        writer.writerows(token_rows)

    print(f"Wrote {len(tags_rows)} tag rows to {tags_path}")
    print(
        f"Wrote {len(token_rows)} token rows to {tokens_path}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())