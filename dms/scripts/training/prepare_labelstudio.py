from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any


def _extract_text(data: dict[str, Any]) -> str:
    for key in ("ocr_text", "text", "content", "document_text"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _extract_choices(results: list[dict[str, Any]], from_name: str) -> list[str]:
    choices: list[str] = []
    for item in results:
        if item.get("from_name") != from_name:
            continue
        value = item.get("value", {})
        selected = value.get("choices") or []
        for choice in selected:
            if isinstance(choice, str):
                choices.append(choice)
    return choices


def _extract_transcriptions(results: list[dict[str, Any]]) -> list[str]:
    texts: list[str] = []
    for item in results:
        value = item.get("value", {})
        if "text" in value and isinstance(value["text"], list):
            for entry in value["text"]:
                if not isinstance(entry, str):
                    continue
                cleaned = entry.strip()
                if not cleaned:
                    continue
                lowered = cleaned.lower()
                if lowered in {"[illegible]", "illegible", "[unreadable]", "unreadable"}:
                    continue
                texts.append(cleaned)
    return texts


def _extract_text_inputs(results: list[dict[str, Any]], from_name: str) -> list[str]:
    entries: list[str] = []
    for item in results:
        if item.get("from_name") != from_name:
            continue
        value = item.get("value", {}) or {}
        raw = value.get("text")
        if isinstance(raw, list):
            for entry in raw:
                if isinstance(entry, str) and entry.strip():
                    entries.append(entry.strip())
        elif isinstance(raw, str) and raw.strip():
            entries.append(raw.strip())
    return entries


def _normalize_due_date_tag(raw: str | None) -> str:
    if not raw:
        return ""
    cleaned = re.sub(r"^\s*due[_\s-]?date\s*[:\-]\s*", "", raw.strip(), flags=re.IGNORECASE)
    match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", cleaned)
    if not match:
        return ""
    value = match.group(1)
    try:
        date.fromisoformat(value)
    except ValueError:
        return ""
    return f"due_date:{value}"


def _find_image_path(data: dict[str, Any]) -> str | None:
    for key in ("image", "image_path", "image_url"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--doc-from-name", default="document_type")
    parser.add_argument("--tags-from-name", default="tags")
    parser.add_argument("--handwriting-from-name", default="handwriting")
    parser.add_argument("--due-date-from-name", default="due_date")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(args.input, "r", encoding="utf-8") as f:
        tasks = json.load(f)

    doc_rows: list[tuple[str, str]] = []
    tag_rows: list[tuple[str, str]] = []
    handwriting_rows: list[tuple[str, str]] = []
    trocr_rows: list[dict[str, str]] = []

    for task in tasks:
        data = task.get("data", {}) or {}
        text = _extract_text(data)
        image_path = _find_image_path(data)

        annotations = task.get("annotations") or []
        if not annotations:
            continue
        results = annotations[0].get("result", []) or []

        doc_type = _extract_choices(results, args.doc_from_name)
        if text and doc_type:
            doc_rows.append((text, doc_type[0]))

        tags = _extract_choices(results, args.tags_from_name)
        due_date_inputs = _extract_text_inputs(results, args.due_date_from_name)
        due_date_raw = due_date_inputs[0] if due_date_inputs else ""
        due_date_tag = _normalize_due_date_tag(due_date_raw) if due_date_raw else ""
        if due_date_raw and not due_date_tag:
            task_id = task.get("id")
            filename = data.get("filename") or data.get("image") or data.get("image_path") or ""
            hint = f"task_id={task_id}" if task_id is not None else "task_id=unknown"
            if filename:
                hint = f"{hint} filename={filename}"
            print(
                f"Warning: invalid due_date value '{due_date_raw}' ({hint}). "
                "Expected format: due_date:YYYY-MM-DD",
                file=sys.stderr,
            )
        tag_set = set(tags)
        if due_date_tag:
            tag_set.add(due_date_tag)
        if text and tag_set:
            tag_rows.append((text, ",".join(sorted(tag_set))))

        handwriting = _extract_choices(results, args.handwriting_from_name)
        if image_path and handwriting:
            handwriting_rows.append((image_path, handwriting[0]))

        transcriptions = _extract_transcriptions(results)
        if image_path and transcriptions:
            for entry in transcriptions:
                trocr_rows.append({"image_path": image_path, "text": entry})

    with open(output_dir / "doc_class.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["text", "label"])
        writer.writerows(doc_rows)

    with open(output_dir / "tags.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["text", "tags"])
        writer.writerows(tag_rows)

    with open(output_dir / "handwriting.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["image_path", "label"])
        writer.writerows(handwriting_rows)

    with open(output_dir / "trocr.jsonl", "w", encoding="utf-8") as f:
        for row in trocr_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print("Prepared datasets:")
    print(f"- {output_dir / 'doc_class.csv'} ({len(doc_rows)} rows)")
    print(f"- {output_dir / 'tags.csv'} ({len(tag_rows)} rows)")
    print(f"- {output_dir / 'handwriting.csv'} ({len(handwriting_rows)} rows)")
    print(f"- {output_dir / 'trocr.jsonl'} ({len(trocr_rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
