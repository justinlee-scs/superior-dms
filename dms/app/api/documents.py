from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from fastapi.responses import StreamingResponse
import io
import mimetypes

from app.db.session import get_db

from app.services.rbac.permission_checker import require_permission
from app.services.rbac.policy import Permissions

from app.db.repositories.documents import (
    create_document,
    create_document_version,
    get_document_by_hash,
    get_document_by_id,
    list_documents,
    update_document_type,
    get_document_version,
    get_document_version_by_id,
    list_document_versions,
    set_current_document_version,
    delete_document as delete_document_repo,
)

from app.schemas.documents import DocumentResponse, DocumentTypeUpdate
from app.schemas.document_versions import (
    DocumentVersionResponse,
    DocumentVersionListItem,
    SetCurrentVersionResponse,
)
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
        set_as_current=True,
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
            version_count=version_count or 1,
            current_version_number=current_version_number or 1,
        )
        for doc, processing_status, CLASSIFICATION, confidence, version_count, current_version_number in rows
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

    current_version = get_document_version(db=db, document_id=document_id)
    versions = list_document_versions(db=db, document_id=document_id)
    current_version_number = None
    if current_version:
        for index, version in enumerate(versions):
            if version.id == current_version.id:
                current_version_number = index + 1
                break

    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        status=current_version.processing_status if current_version else None,
        document_type=document.document_type,
        confidence=current_version.confidence if current_version else None,
        created_at=document.created_at,
        current_version_id=document.current_version_id,
        version_count=len(versions) or 1,
        current_version_number=current_version_number or 1,
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


@router.get("/{document_id}/versions", response_model=list[DocumentVersionListItem])
def get_document_versions(
    document_id: UUID,
    db: Session = Depends(get_db),
    _=Depends(require_permission(Permissions.DOCUMENT_VERSION_READ)),
):
    document = get_document_by_id(db=db, document_id=document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    versions = list_document_versions(db=db, document_id=document_id)
    return [
        DocumentVersionListItem(
            id=version.id,
            document_id=version.document_id,
            version_number=index + 1,
            is_current=document.current_version_id == version.id,
            processing_status=version.processing_status,
            classification=version.classification,
            confidence=version.confidence,
            created_at=version.created_at,
            size_bytes=len(version.content) if version.content else 0,
        )
        for index, version in enumerate(versions)
    ]


@router.post(
    "/{document_id}/versions",
    response_model=DocumentVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_new_document_version(
    document_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _=Depends(require_permission(Permissions.DOCUMENT_VERSION_CREATE)),
):
    document = get_document_by_id(db=db, document_id=document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    version = create_document_version(
        db=db,
        document_id=document_id,
        file_bytes=file_bytes,
        set_as_current=True,
    )

    # Keep canonical display name aligned with latest uploaded version.
    if file.filename:
        document.filename = file.filename
        db.commit()
        db.refresh(document)

    process_document(db=db, version_id=version.id, file_bytes=file_bytes)
    return version


@router.post(
    "/{document_id}/versions/{version_id}/set-current",
    response_model=SetCurrentVersionResponse,
)
def set_current_version(
    document_id: UUID,
    version_id: UUID,
    db: Session = Depends(get_db),
    _=Depends(require_permission(Permissions.DOCUMENT_VERSION_SET_CURRENT)),
):
    document = get_document_by_id(db=db, document_id=document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    version = get_document_version_by_id(db=db, version_id=version_id)
    if not version or version.document_id != document.id:
        raise HTTPException(status_code=404, detail="Document version not found")

    set_current_document_version(db=db, document=document, version=version)
    return SetCurrentVersionResponse(
        status="ok",
        document_id=document.id,
        current_version_id=version.id,
    )


@router.get("/{document_id}/versions/{version_id}/download")
def download_document_version(
    document_id: UUID,
    version_id: UUID,
    db: Session = Depends(get_db),
    _=Depends(require_permission(Permissions.DOCUMENT_VERSION_DOWNLOAD)),
):
    version = get_document_version_by_id(db=db, version_id=version_id)
    if not version or version.document_id != document_id:
        raise HTTPException(status_code=404, detail="File version not found")

    return StreamingResponse(
        io.BytesIO(version.content),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{version.document.filename}"'
        },
    )


@router.get("/{document_id}/versions/{version_id}/preview")
def preview_document_version(
    document_id: UUID,
    version_id: UUID,
    db: Session = Depends(get_db),
    _=Depends(require_permission(Permissions.DOCUMENT_VERSION_PREVIEW)),
):
    version = get_document_version_by_id(db=db, version_id=version_id)
    if not version or version.document_id != document_id:
        raise HTTPException(status_code=404, detail="File version not found")

    filename = version.document.filename
    mime_type, _ = mimetypes.guess_type(filename)
    mime_type = mime_type or "application/octet-stream"

    return StreamingResponse(
        io.BytesIO(version.content),
        media_type=mime_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
