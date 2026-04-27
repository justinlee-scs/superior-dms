from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from app.db.models.training_feedback_event import TrainingFeedbackEvent
from app.db.session import SessionLocal


def _read_rows(path: Path) -> list[list[str]]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
    return rows[1:] if rows else []


def _write_rows(path: Path, header: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--doc-class", required=True)
    parser.add_argument("--tags", required=True)
    args = parser.parse_args()

    doc_path = Path(args.doc_class)
    tags_path = Path(args.tags)

    doc_rows = _read_rows(doc_path)
    tags_rows = _read_rows(tags_path)

    doc_seen = {(r[0], r[1]) for r in doc_rows if len(r) >= 2}
    tags_seen = {(r[0], r[1]) for r in tags_rows if len(r) >= 2}

    added_doc = 0
    added_tags = 0

    db: Session = SessionLocal()
    try:
        events = (
            db.query(TrainingFeedbackEvent)
            .filter(TrainingFeedbackEvent.include_in_training.is_(True))
            .order_by(TrainingFeedbackEvent.created_at.asc())
            .all()
        )

        for ev in events:
            text = (ev.extracted_text_snapshot or "").strip()
            if not text:
                continue

            if ev.final_document_type:
                key = (text, ev.final_document_type)
                if key not in doc_seen:
                    doc_rows.append([text, ev.final_document_type])
                    doc_seen.add(key)
                    added_doc += 1

            final_tags = [t for t in (ev.final_tags or []) if isinstance(t, str) and t]
            if final_tags:
                merged = ",".join(sorted(set(final_tags)))
                key = (text, merged)
                if key not in tags_seen:
                    tags_rows.append([text, merged])
                    tags_seen.add(key)
                    added_tags += 1
    finally:
        db.close()

    _write_rows(doc_path, ["text", "label"], doc_rows)
    _write_rows(tags_path, ["text", "tags"], tags_rows)

    print(
        f"Augmented training datasets from feedback: +{added_doc} doc_class rows, +{added_tags} tags rows."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
