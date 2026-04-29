from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_db
from app.db.repositories.documents import get_document, reset_processing_state
from app.workers.processor import enqueue_processing
from app.services.rbac.permission_checker import require_permission
from app.services.rbac.policy import Permissions

router = APIRouter(prefix="/processing", tags=["processing"])


@router.post("/documents/{document_id}/process", status_code=202)
def process_document(
    document_id: UUID,
    db: Session = Depends(get_db),
):
    """Trigger processing for an existing document.

    Parameters:
        document_id (type=str): Identifier used to locate the target record.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
    """

    document = get_document(db, document_id)

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if not document.current_version_id:
        raise HTTPException(status_code=409, detail="Document has no current version")

    enqueue_processing(str(document.current_version_id))

    return {
        "document_id": document_id,
        "status": "processing_started",
    }


@router.post("/documents/{document_id}/reprocess", status_code=202)
def reprocess_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    _=Depends(require_permission(Permissions.DOCUMENT_UPDATE)),
):
    """Force reprocessing (new OCR run, same document version).

    Parameters:
        document_id (type=str): Identifier used to locate the target record.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
    """

    document = get_document(db, document_id)

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if not document.current_version_id:
        raise HTTPException(status_code=409, detail="Document has no current version")

    reset_processing_state(db, document.current_version_id)
    enqueue_processing(str(document.current_version_id))

    return {
        "document_id": document_id,
        "status": "reprocessing_started",
    }
