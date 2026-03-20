from __future__ import annotations

import argparse
import json
from pathlib import Path

from pdf2image import convert_from_path


def _safe_name(name: str) -> str:
    cleaned = []
    for ch in name:
        if ch.isalnum() or ch in {"-", "_"}:
            cleaned.append(ch)
        elif ch in {" ", ".", "#"}:
            cleaned.append("_")
        else:
            cleaned.append("_")
    return "".join(cleaned).strip("_")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--dpi", type=int, default=200)
    parser.add_argument("--tasks", required=False, help="Optional tasks JSON output")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    tasks = []
    for pdf_path in sorted(input_dir.rglob("*.pdf")):
        pages = convert_from_path(str(pdf_path), dpi=args.dpi)
        safe_stem = _safe_name(pdf_path.stem)
        for index, page in enumerate(pages, start=1):
            filename = f"{safe_stem}_page_{index:03d}.png"
            image_path = output_dir / filename
            page.save(image_path, "PNG")
            tasks.append(
                {
                    "data": {
                        "image": str(image_path),
                        "filename": pdf_path.name,
                        "page": index,
                    }
                }
            )

    if args.tasks:
        tasks_path = Path(args.tasks)
        tasks_path.parent.mkdir(parents=True, exist_ok=True)
        with open(tasks_path, "w", encoding="utf-8") as f:
            json.dump(tasks, f, ensure_ascii=False, indent=2)
        print(f"Saved tasks to {tasks_path}")

    print(f"Exported {len(tasks)} page images to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
