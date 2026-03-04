import uuid

from app.db.repositories.documents import (
    create_document,
    create_document_version,
    delete_document,
    get_document_by_id,
    get_document_version,
)
from app.db.session import SessionLocal


def main() -> None:
    db = SessionLocal()
    doc = None

    try:
        unique_suffix = uuid.uuid4().hex[:8]
        filename = f"smoke-test-{unique_suffix}.txt"
        content_hash = uuid.uuid4().hex
        file_bytes = b"database smoke test"

        doc = create_document(
            db=db,
            filename=filename,
            content_hash=content_hash,
        )
        version = create_document_version(
            db=db,
            document_id=doc.id,
            file_bytes=file_bytes,
        )

        fetched_doc = get_document_by_id(db=db, document_id=doc.id)
        fetched_version = get_document_version(db=db, document_id=doc.id)

        assert fetched_doc is not None, "document was not persisted"
        assert fetched_version is not None, "document version was not persisted"
        assert version.id == fetched_version.id, "unexpected active version id"

        print(f"DB smoke test passed. document_id={doc.id} version_id={version.id}")

    finally:
        if doc is not None:
            delete_document(db=db, document_id=doc.id)
        db.close()


if __name__ == "__main__":
    main()
