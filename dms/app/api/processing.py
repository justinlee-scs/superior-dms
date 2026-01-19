from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db import repositories
from app.workers.processor import enqueue_processing

router = APIRouter(prefix="/processing", tags=["processing"])


@router.post("/documents/{document_id}/process", status_code=202)
def process_document(
    document_id: str,
    db: Session = Depends(get_db),
):
    """
    Trigger processing for an existing document.
    """

    document = repositories.get_document(db, document_id)

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    enqueue_processing(document.current_version_id)

    return {
        "document_id": document_id,
        "status": "processing_started",
    }


@router.post("/documents/{document_id}/reprocess", status_code=202)
def reprocess_document(
    document_id: str,
    db: Session = Depends(get_db),
):
    """
    Force reprocessing (new OCR run, same document version).
    """

    document = repositories.get_document(db, document_id)

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    repositories.reset_processing_state(db, document.current_version_id)
    enqueue_processing(document.current_version_id)

    return {
        "document_id": document_id,
        "status": "reprocessing_started",
    }
