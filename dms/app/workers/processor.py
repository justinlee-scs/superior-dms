import os
import logging
from concurrent.futures import ThreadPoolExecutor
import threading
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.processing.pipeline import process_document
from app.db.repositories.documents import load_document_version_bytes
from app.db.models.document_versions import DocumentVersion
from app.db.models.enums import ProcessingStatus
from app.db.session import SessionLocal


logger = logging.getLogger(__name__)


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
        logger.info("Processing started version_id=%s", normalized_version_id)
        # Commit immediately so UI does not remain on processing while OCR runs.
        version.processing_status = ProcessingStatus.processing
        db.commit()

        file_bytes = load_document_version_bytes(db, normalized_version_id)

        process_document(
            db=db,
            version_id=normalized_version_id,
            file_bytes=file_bytes,
            commit=True,
        )
        logger.info("Processing finished version_id=%s", normalized_version_id)

    except Exception:
        version = db.get(DocumentVersion, normalized_version_id)
        if version:
            version.processing_status = ProcessingStatus.failed
            db.commit()
        logger.exception("Processing failed version_id=%s", normalized_version_id)
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


def recover_stuck_processing_jobs() -> int:
    """Requeue any versions left in processing after a crash or restart."""
    db = SessionLocal()
    try:
        lock_key = 482_915_731_204_817
        got_lock = db.execute(
            text("SELECT pg_try_advisory_lock(:lock_key)"),
            {"lock_key": lock_key},
        ).scalar()
        if not got_lock:
            return 0

        stale_versions = (
            db.query(DocumentVersion.id)
            .filter(
                DocumentVersion.processing_status == ProcessingStatus.processing
            )
            .order_by(DocumentVersion.created_at.asc())
            .all()
        )

        requeued = 0
        for (version_id,) in stale_versions:
            try:
                enqueue_processing(version_id)
                requeued += 1
                logger.warning(
                    "Requeued stale processing job version_id=%s", version_id
                )
            except RuntimeError as exc:
                logger.warning(
                    "Processing queue full while recovering version_id=%s: %s",
                    version_id,
                    exc,
                )
                break

        return requeued
    finally:
        db.close()
