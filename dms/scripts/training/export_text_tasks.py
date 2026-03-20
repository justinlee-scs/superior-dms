from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from app.services.extraction.ocr_sync import extract_text_with_metadata


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    tasks: list[dict[str, object]] = []

    for pdf_path in sorted(input_dir.rglob("*.pdf")):
        file_bytes = pdf_path.read_bytes()
        extraction = extract_text_with_metadata(
            file_bytes=file_bytes,
            filename=pdf_path.name,
        )
        text = extraction.text or ""
        tasks.append(
            {
                "data": {
                    "ocr_text": text,
                    "filename": pdf_path.name,
                    "document_id": pdf_path.stem,
                }
            }
        )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(tasks)} text tasks to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
