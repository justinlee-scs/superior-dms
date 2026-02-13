from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from fastapi.responses import StreamingResponse
import io
import mimetypes

from app.db.session import get_db
from app.deps import require_role #remove?

from app.services.rbac.permission_checker import require_permission
from app.db.models.user import User
from app.services.rbac.policy import Permissions

from app.db.repositories.documents import (
    create_document,
    create_document_version,
    get_document_by_hash,
    get_document_by_id,
    list_documents,
    update_document_type,
    get_document_version,
    delete_document as delete_document_repo,
)

from app.schemas.documents import DocumentResponse, DocumentTypeUpdate
from app.schemas.document_versions import DocumentVersionResponse
from app.processing.pipeline import process_document


router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    #_=Depends(require_role("editor")),
    _=Depends(require_permission(Permissions.DOCUMENT_UPLOAD)),
):
    file_bytes = await file.read()

    from app.services.hash import compute_content_hash
    content_hash = compute_content_hash(file_bytes)

    existing = get_document_by_hash(db=db, content_hash=content_hash)
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
        file_bytes=file_bytes,
    )

    process_document(db=db, version_id=version.id, file_bytes=file_bytes)

    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        status=version.processing_status,
        document_type=document.document_type,
        confidence=version.confidence,
        created_at=document.created_at,
        current_version_id=version.id,
    )


@router.get("/", response_model=list[DocumentResponse])
def get_documents(
    db: Session = Depends(get_db),
    #_=Depends(require_role("viewer")), #what if we comment out the viewing thing real quick one time
    _=Depends(require_permission(Permissions.DOCUMENT_READ)),
):
    rows = list_documents(db=db)

    return [
        DocumentResponse(
            id=doc.id,
            filename=doc.filename,
            status=processing_status,
            document_type=doc.document_type or CLASSIFICATION,
            confidence=confidence,
            created_at=doc.created_at,
            current_version_id=doc.current_version_id,
        )
        for doc, processing_status, CLASSIFICATION, confidence in rows
    ]


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    #_=Depends(require_role("viewer")),
    _=Depends(require_permission(Permissions.DOCUMENT_READ)),
):
    document = get_document_by_id(db=db, document_id=document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        status=document.status,
        document_type=document.document_type,
        confidence=document.confidence,
        created_at=document.created_at,
        current_version_id=document.current_version_id,
    )


@router.patch("/{document_id}/type", response_model=DocumentResponse)
def set_document_type(
    document_id: UUID,
    payload: DocumentTypeUpdate,
    db: Session = Depends(get_db),
    #_=Depends(require_role("editor")),
    _=Depends(require_permission(Permissions.DOCUMENT_UPDATE)),
):
    document = update_document_type(
        db=db,
        document_id=document_id,
        document_type=payload.document_type,
    )

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        status=document.status,
        document_type=document.document_type,
        confidence=document.confidence,
        created_at=document.created_at,
        current_version_id=document.current_version_id,
    )


@router.get("/{document_id}/output", response_model=DocumentVersionResponse)
def get_document_output(
    document_id: UUID,
    db: Session = Depends(get_db),
    #_=Depends(require_role("viewer")),
    _=Depends(require_permission(Permissions.DOCUMENT_READ)),
):
    version = get_document_version(db=db, document_id=document_id)
    if not version:
        raise HTTPException(status_code=404, detail="No processed version available")
    return version


@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    #_=Depends(require_role("admin")),
    _=Depends(require_permission(Permissions.DOCUMENT_DELETE)),
):
    document = get_document_by_id(db=db, document_id=document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    delete_document_repo(db=db, document_id=document_id)


@router.get("/{document_id}/download")
def download_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    #_=Depends(require_role("viewer")),
    _=Depends(require_permission(Permissions.DOCUMENT_DOWNLOAD)),
):
    version = get_document_version(db=db, document_id=document_id)
    if not version:
        raise HTTPException(status_code=404, detail="File not found")

    return StreamingResponse(
        io.BytesIO(version.content),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{version.document.filename}"'
        },
    )


@router.get("/{document_id}/preview")
def preview_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    #_=Depends(require_role("viewer")),
    _=Depends(require_permission(Permissions.DOCUMENT_PREVIEW)),
):
    version = get_document_version(db=db, document_id=document_id)
    if not version:
        raise HTTPException(status_code=404, detail="File not found")

    filename = version.document.filename
    mime_type, _ = mimetypes.guess_type(filename)
    mime_type = mime_type or "application/octet-stream"

    return StreamingResponse(
        io.BytesIO(version.content),
        media_type=mime_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
