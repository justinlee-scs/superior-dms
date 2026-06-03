from __future__ import annotations

import argparse
import csv
from pathlib import Path


def _read(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = [dict(row) for row in reader]
        header = list(reader.fieldnames or [])
    return header, rows


def _write(path: Path, header: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in header})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--extra", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    base_header, base_rows = _read(Path(args.base))
    extra_header, extra_rows = _read(Path(args.extra))
    header = base_header or extra_header
    if not header:
        raise SystemExit("CSV inputs do not contain headers.")

    seen = {
        tuple((row.get(col, "") or "") for col in header)
        for row in base_rows
    }
    merged = list(base_rows)
    for row in extra_rows:
        key = tuple((row.get(col, "") or "") for col in header)
        if key in seen:
            continue
        seen.add(key)
        merged.append(row)

    _write(Path(args.output), header, merged)
    print(f"Merged {len(base_rows)} + {len(extra_rows)} rows -> {len(merged)} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
