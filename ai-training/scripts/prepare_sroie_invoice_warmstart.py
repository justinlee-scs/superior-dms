#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

from PIL import Image

try:
    from pytesseract import Output
    import pytesseract
except Exception as exc:  # pragma: no cover - optional dependency guard
    raise SystemExit(
        "pytesseract is required for prepare_sroie_invoice_warmstart.py"
    ) from exc


@dataclass(frozen=True)
class Token:
    text: str
    x: float
    y: float
    w: float
    h: float
    page: int = 1


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _norm_compare(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def _parse_date(value: str) -> str:
    value = _clean(value)
    if not value:
        return ""
    for pattern in (
        r"\b(\d{4})-(\d{2})-(\d{2})\b",
        r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b",
        r"\b(\d{1,2})-(\d{1,2})-(\d{2,4})\b",
    ):
        match = re.search(pattern, value)
        if not match:
            continue
        if len(match.groups()) == 3 and len(match.group(1)) == 4:
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


def _normalize_money(value: str) -> str:
    cleaned = _clean(value)
    if not cleaned:
        return ""
    cleaned = cleaned.replace(",", "")
    match = re.search(r"(\d+(?:\.\d{1,2})?)", cleaned)
    if not match:
        return ""
    return match.group(1)


def _load_image(path: Path) -> Image.Image:
    return Image.open(path).convert("RGB")


def _ocr_tokens(image: Image.Image) -> list[Token]:
    data = pytesseract.image_to_data(image, output_type=Output.DICT)
    width, height = image.size
    tokens: list[Token] = []
    for i, text in enumerate(data.get("text", [])):
        cleaned = _clean(str(text))
        if not cleaned:
            continue
        try:
            conf = float(data.get("conf", [0])[i])
        except Exception:
            conf = 0.0
        if conf < 0:
            continue
        x = float(data.get("left", [0])[i])
        y = float(data.get("top", [0])[i])
        w = float(data.get("width", [0])[i])
        h = float(data.get("height", [0])[i])
        tokens.append(
            Token(
                text=cleaned,
                x=x / width if width else 0.0,
                y=y / height if height else 0.0,
                w=w / width if width else 0.0,
                h=h / height if height else 0.0,
            )
        )
    return tokens


def _find_span(tokens: list[Token], value: str) -> tuple[int, int] | None:
    parts = [_norm_compare(part) for part in re.split(r"\s+", value) if _norm_compare(part)]
    if not parts:
        return None
    normalized = [_norm_compare(tok.text) for tok in tokens]

    for start in range(len(normalized)):
        if normalized[start] != parts[0]:
            continue
        end = start
        pi = 0
        ti = start
        while pi < len(parts) and ti < len(normalized):
            if normalized[ti] == parts[pi]:
                pi += 1
            ti += 1
        if pi == len(parts):
            return start, ti
    return None


def _label_tokens(tokens: list[Token], annotations: dict[str, str]) -> list[str]:
    labels = ["O"] * len(tokens)

    def apply(field: str, value: str) -> None:
        value = _clean(value)
        if not value:
            return
        span = _find_span(tokens, value)
        if span is None and field in {"document_date", "due_date"}:
            iso = _parse_date(value)
            if iso:
                span = _find_span(tokens, iso)
        if span is None and field == "grand_total":
            money = _normalize_money(value)
            if money:
                span = _find_span(tokens, money)
        if span is None:
            return
        start, end = span
        for idx in range(start, min(end, len(labels))):
            labels[idx] = field

    apply("company", annotations.get("company") or annotations.get("vendor") or "")
    apply("document_date", annotations.get("document_date") or annotations.get("date") or "")
    apply("due_date", annotations.get("due_date") or "")
    apply("grand_total", annotations.get("grand_total") or annotations.get("total") or "")
    apply("bill_to", annotations.get("bill_to") or annotations.get("address") or "")
    apply("invoice_number", annotations.get("invoice_number") or annotations.get("invoice_no") or "")

    return labels


def _build_tags(annotations: dict[str, str]) -> list[str]:
    tags: list[str] = []

    company = _clean(annotations.get("company") or annotations.get("vendor") or "")
    if company:
        tags.append(f"company:{company}")

    document_date = _parse_date(annotations.get("document_date") or annotations.get("date") or "")
    if document_date:
        tags.append(f"document_date:{document_date}")

    due_date = _parse_date(annotations.get("due_date") or "")
    if due_date:
        tags.append(f"due_date:{due_date}")

    total = _normalize_money(annotations.get("grand_total") or annotations.get("total") or "")
    if total:
        tags.append(f"grand_total:{total}")

    bill_to = _clean(annotations.get("bill_to") or annotations.get("address") or "")
    if bill_to:
        tags.append(f"bill_to:{bill_to}")

    invoice_number = _clean(annotations.get("invoice_number") or annotations.get("invoice_no") or "")
    if invoice_number:
        tags.append(f"invoice_number:{invoice_number}")

    return sorted(set(tags))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-csv", required=True, help="Flattened SROIE/invoice annotation CSV")
    parser.add_argument("--output-dir", required=True, help="Directory for tags.csv and field_tokens.csv")
    parser.add_argument(
        "--image-root",
        default="",
        help="Optional root used to resolve relative image paths in the CSV.",
    )
    args = parser.parse_args()

    input_csv = Path(args.input_csv)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    image_root = Path(args.image_root).resolve() if args.image_root else None

    rows = _read_rows(input_csv)

    tags_rows: list[tuple[str, str]] = []
    token_rows: list[list[str]] = []

    for idx, row in enumerate(rows):
        image_ref = _clean(row.get("image_path") or row.get("image") or row.get("image_file") or "")
        if not image_ref:
            continue
        image_path = Path(image_ref)
        if not image_path.exists() and image_root is not None:
            image_path = image_root / image_ref
        if not image_path.exists():
            continue

        annotations = {
            "company": row.get("company") or row.get("vendor") or row.get("vendor_name") or "",
            "document_date": row.get("document_date") or row.get("date") or "",
            "due_date": row.get("due_date") or "",
            "grand_total": row.get("grand_total") or row.get("total") or "",
            "bill_to": row.get("bill_to") or row.get("address") or "",
            "invoice_number": row.get("invoice_number") or row.get("invoice_no") or "",
        }

        image = _load_image(image_path)
        tokens = _ocr_tokens(image)
        labels = _label_tokens(tokens, annotations)
        tags = _build_tags(annotations)

        text = " ".join(tok.text for tok in tokens).strip()
        if text and tags:
            tags_rows.append((text, ",".join(tags)))

        task_id = row.get("task_id") or f"sroie_{idx:06d}"
        for tok, label in zip(tokens, labels):
            token_rows.append(
                [
                    tok.text,
                    f"{tok.x:.6f}",
                    f"{tok.y:.6f}",
                    f"{tok.w:.6f}",
                    f"{tok.h:.6f}",
                    "1",
                    label,
                    task_id,
                    image_path.name,
                    str(image_path),
                ]
            )

    with (output_dir / "tags.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["text", "tags"])
        writer.writerows(tags_rows)

    with (output_dir / "field_tokens.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["text", "x", "y", "w", "h", "page", "label", "task_id", "filename", "image_path"])
        writer.writerows(token_rows)

    print(f"Wrote {len(tags_rows)} tag rows to {output_dir / 'tags.csv'}")
    print(f"Wrote {len(token_rows)} token rows to {output_dir / 'field_tokens.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
