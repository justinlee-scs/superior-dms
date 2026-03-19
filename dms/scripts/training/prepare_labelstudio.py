from __future__ import annotations

import argparse
import csv
import json
import os
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
                if isinstance(entry, str) and entry.strip():
                    texts.append(entry.strip())
    return texts


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
        if text and tags:
            tag_rows.append((text, ",".join(sorted(set(tags)))))

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
