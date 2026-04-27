from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from pdf2image import convert_from_path

import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from app.services.extraction.ocr_sync import extract_text_with_metadata


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


def _chunk(items: list[Path], size: int) -> Iterable[list[Path]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _export_ocr_images(
    pdfs: list[Path],
    *,
    output_dir: Path,
    tasks_path: Path,
    url_prefix: str,
    dpi: int,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    tasks: list[dict[str, object]] = []

    for pdf_path in pdfs:
        try:
            pages = convert_from_path(str(pdf_path), dpi=dpi)
        except Exception as exc:
            print(f"Skipping {pdf_path}: {exc}")
            continue
        safe_stem = _safe_name(pdf_path.stem)
        for index, page in enumerate(pages, start=1):
            filename = f"{safe_stem}_page_{index:03d}.png"
            image_path = output_dir / filename
            page.save(image_path, "PNG")
            tasks.append(
                {
                    "data": {
                        "image": f"{url_prefix}/{filename}",
                        "filename": pdf_path.name,
                        "page": index,
                    }
                }
            )

    tasks_path.parent.mkdir(parents=True, exist_ok=True)
    tasks_path.write_text(json.dumps(tasks, ensure_ascii=False, indent=2))


def _labelstudio_image_prefix(*, image_mode: str, image_port: int, dataset_key: str) -> str:
    mode = image_mode.strip().lower()
    if mode in {"localhost", "http", "image-server"}:
        # docker-compose mounts ./output to /images for the HTTP server.
        return f"http://localhost:{image_port}/training/ocr_images/{dataset_key}"
    # docker-compose mounts ./output to /data/media for Label Studio local-files.
    return f"/data/local-files/?d=training/ocr_images/{dataset_key}"


def _export_text_tasks(pdfs: list[Path], *, output_path: Path) -> None:
    tasks: list[dict[str, object]] = []
    for pdf_path in pdfs:
        try:
            file_bytes = pdf_path.read_bytes()
            extraction = extract_text_with_metadata(
                file_bytes=file_bytes,
                filename=pdf_path.name,
            )
        except Exception as exc:
            print(f"Skipping text for {pdf_path}: {exc}")
            continue
        tasks.append(
            {
                "data": {
                    "ocr_text": extraction.text or "",
                    "filename": pdf_path.name,
                    "document_id": pdf_path.stem,
                }
            }
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(tasks, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, help="Root folder containing PDFs")
    parser.add_argument(
        "--rapid-folder",
        default="Rapid Tire Repair - use as handwriting sample",
        help="Folder name for rapid tire repair",
    )
    parser.add_argument("--batch-size", type=int, default=200)
    parser.add_argument("--max-batches", type=int, default=8)
    parser.add_argument("--other-folder", default="test maybe")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dpi", type=int, default=200)
    parser.add_argument(
        "--output-root",
        default="/home/justinlee/.LINUXPRACTICE/dms/output/training",
    )
    parser.add_argument("--image-port", type=int, default=8089)
    parser.add_argument(
        "--image-mode",
        default="local-files",
        choices=["local-files", "localhost", "http", "image-server"],
        help="How image URLs are written into ocr_tasks.json.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    output_root = Path(args.output_root).resolve()
    image_root = output_root / "ocr_images"

    rapid_dir = root / args.rapid_folder
    if not rapid_dir.exists():
        raise SystemExit(f"Rapid folder not found: {rapid_dir}")

    rapid_pdfs = sorted(rapid_dir.rglob("*.pdf"))
    other_dir = root / args.other_folder
    if not other_dir.exists():
        raise SystemExit(f"Other folder not found: {other_dir}")
    other_pdfs = sorted(other_dir.rglob("*.pdf"))

    # Rapid dataset (single)
    rapid_out = output_root / "rapid_tire_repair"
    rapid_img_dir = image_root / "rapid_tire_repair"
    _export_ocr_images(
        rapid_pdfs,
        output_dir=rapid_img_dir,
        tasks_path=rapid_out / "ocr_tasks.json",
        url_prefix=_labelstudio_image_prefix(
            image_mode=args.image_mode,
            image_port=args.image_port,
            dataset_key="rapid_tire_repair",
        ),
        dpi=args.dpi,
    )
    _export_text_tasks(rapid_pdfs, output_path=rapid_out / "text_tasks.json")

    # Other dataset (batches)
    batch_root = output_root / "batches"
    existing_batches = sorted(p for p in batch_root.glob("batch_*") if p.is_dir())
    skip_batches = 0
    if args.resume and existing_batches:
        skip_batches = len(existing_batches)
    start_index = skip_batches * args.batch_size
    remaining = other_pdfs[start_index:]
    max_batches = max(0, args.max_batches - skip_batches)

    for idx, batch in enumerate(_chunk(remaining, args.batch_size), start=skip_batches + 1):
        if idx - skip_batches > max_batches:
            break
        batch_name = f"batch_{idx:03d}"
        batch_out = batch_root / batch_name
        batch_img_dir = image_root / batch_name
        _export_ocr_images(
            batch,
            output_dir=batch_img_dir,
            tasks_path=batch_out / "ocr_tasks.json",
            url_prefix=_labelstudio_image_prefix(
                image_mode=args.image_mode,
                image_port=args.image_port,
                dataset_key=batch_name,
            ),
            dpi=args.dpi,
        )
        _export_text_tasks(batch, output_path=batch_out / "text_tasks.json")

    print(f"Rapid dataset: {rapid_out}")
    print(f"Other batches: {batch_root}")
    print(f"OCR images root: {image_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
