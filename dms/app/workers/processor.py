from sqlalchemy.orm import Session

from app.processing.pipeline import process_document


def enqueue_processing(
    db: Session,
    version_id: str,
    file_bytes: bytes,
):
    """
    Temporary synchronous processor.
    Later replaced by async worker / queue.
    """
    process_document(
        db=db,
        version_id=version_id,
        file_bytes=file_bytes,
    )
