from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime

from app.db.session import get_db
from app.db.repositories.documents import (
    create_document,
    create_document_version,
    get_document_by_hash,
    get_document_by_id,
    list_documents,
)
from app.processing.pipeline import process_document
from app.services.hash import compute_content_hash

from app.schemas.documents import DocumentResponse

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
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

    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        status=document.status,
        document_type=document.document_type,
        confidence=document.confidence,
        created_at=document.created_at,
    )


@router.get(
    "/",
    response_model=list[DocumentResponse],
)
def get_documents(
    db: Session = Depends(get_db),
):
    documents = list_documents(db=db)

    return [
        DocumentResponse(
            id=d.id,
            filename=d.filename,
            status=d.status,
            document_type=d.document_type,
            confidence=d.confidence,
            created_at=d.created_at,
        )
        for d in documents
    ]


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
)
def get_document(
    document_id: UUID,
    db: Session = Depends(get_db),
):
    document = get_document_by_id(
        db=db,
        document_id=document_id,
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        status=document.status,
        document_type=document.document_type,
        confidence=document.confidence,
        created_at=document.created_at,
    )
