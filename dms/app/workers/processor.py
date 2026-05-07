import os
from concurrent.futures import ThreadPoolExecutor
import threading
from uuid import UUID

from sqlalchemy.orm import Session

from app.processing.pipeline import process_document
from app.db.repositories.documents import load_document_version_bytes
from app.db.models.document_versions import DocumentVersion
from app.db.models.enums import ProcessingStatus
from app.db.session import SessionLocal


def process_document_version(db: Session, version_id: str | UUID) -> None:
    """Synchronous processor for a DocumentVersion."""

    try:
        normalized_version_id = UUID(str(version_id))
    except (TypeError, ValueError):
        normalized_version_id = version_id

    version = db.get(DocumentVersion, normalized_version_id)
    if not version:
        return

    try:
        # Commit immediately so UI does not remain at "pending" while OCR runs.
        version.processing_status = ProcessingStatus.processing
        db.commit()

        file_bytes = load_document_version_bytes(db, normalized_version_id)

        process_document(
            db=db,
            version_id=normalized_version_id,
            file_bytes=file_bytes,
            commit=True,
        )

    except Exception:
        version = db.get(DocumentVersion, normalized_version_id)
        if version:
            version.processing_status = ProcessingStatus.failed
            db.commit()
        raise


def _process_in_background(version_id: str | UUID) -> None:
    db = SessionLocal()
    try:
        process_document_version(db, version_id)
    finally:
        db.close()


_MAX_WORKERS = max(1, int(os.getenv("PROCESSING_MAX_WORKERS", "4")))
_MAX_QUEUE_SIZE = max(1, int(os.getenv("PROCESSING_MAX_QUEUE_SIZE", "200")))
_EXECUTOR = ThreadPoolExecutor(max_workers=_MAX_WORKERS, thread_name_prefix="docproc")
_QUEUE_LOCK = threading.Lock()
_QUEUED = 0


def enqueue_processing(version_id: str | UUID) -> None:
    """Queue processing in a bounded in-process executor.

    Raises RuntimeError when queue capacity is reached.
    """
    global _QUEUED
    with _QUEUE_LOCK:
        if _QUEUED >= _MAX_QUEUE_SIZE:
            raise RuntimeError(
                f"Processing queue is full ({_MAX_QUEUE_SIZE}); try again shortly"
            )
        _QUEUED += 1

    def _run() -> None:
        try:
            _process_in_background(version_id)
        finally:
            global _QUEUED
            with _QUEUE_LOCK:
                _QUEUED = max(0, _QUEUED - 1)

    _EXECUTOR.submit(_run)


def enqueue_document_processing(version_id: str | UUID) -> None:
    """Backward-compatible alias used by document upload endpoints."""
    enqueue_processing(version_id)
