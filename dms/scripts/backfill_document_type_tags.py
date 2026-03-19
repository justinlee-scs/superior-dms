from __future__ import annotations

import sys

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models.document_versions import DocumentVersion
from app.db.repositories.documents import replace_document_version_tags


def _needs_doc_type_tag(tags: list[str]) -> bool:
    return not any(tag.startswith("document_type:") for tag in (tags or []))


def _derived_doc_type(classification: str | None) -> str | None:
    if not classification:
        return None
    return f"document_type:{classification}"


def backfill(db: Session) -> int:
    count = 0
    rows = db.query(DocumentVersion).all()
    for version in rows:
        tags = list(version.tags or [])
        if not _needs_doc_type_tag(tags):
            continue
        doc_type = _derived_doc_type(
            version.classification.value if version.classification else None
        )
        if not doc_type:
            continue
        tags.append(doc_type)
        replace_document_version_tags(db=db, version=version, tags=tags)
        count += 1
    db.commit()
    return count


def main() -> int:
    db = SessionLocal()
    try:
        updated = backfill(db)
    finally:
        db.close()
    print(f"Updated {updated} document versions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
