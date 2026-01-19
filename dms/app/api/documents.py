from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.repositories.documents import (
    create_document,
    create_document_version,
    get_document_by_hash,
)
from app.processing.pipeline import process_document
from app.services.hash import compute_content_hash

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    file_bytes = await file.read()
    content_hash = compute_content_hash(file_bytes)

    # DUPLICATE CHECK
    existing = get_document_by_hash(
        db=db,
        content_hash=content_hash,
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document with identical content already exists",
        )

    document = create_document(
        db=db,
        filename=file.filename,
        content_hash=content_hash,
    )

    version = create_document_version(
        db=db,
        document_id=document.id,
    )

    process_document(
        db=db,
        version_id=version.id,
        file_bytes=file_bytes,
    )

    return {
        "document_id": document.id,
        "version_id": version.id,
        "status": "processed",
    }
