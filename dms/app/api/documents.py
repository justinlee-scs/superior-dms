from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID, uuid4
from fastapi.responses import StreamingResponse
import io
import mimetypes
import tempfile
import zipfile
from datetime import datetime, timezone, date, timedelta
from pathlib import Path
import os

from PIL import Image, UnidentifiedImageError

from app.db.session import get_db
from app.auth.deps import get_current_user
from app.db.models.user import User

from app.services.rbac.permission_checker import require_permission
from app.services.rbac.policy import Permissions

from app.db.repositories.documents import (
    add_document_version_tags,
    create_document,
    create_document_version,
    get_document_by_hash,
    get_document_by_id,
    list_documents,
    list_upcoming_due_payments,
    remove_document_version_tags,
    replace_document_version_tags,
    update_document_type,
    get_document_version,
    get_document_version_by_id,
    list_document_versions,
    set_current_document_version,
    delete_document as delete_document_repo,
    list_existing_tags,
    load_document_version_bytes,
)
from app.db.repositories.tags import create_tag_pool_entry, list_tag_pool

from app.schemas.documents import (
    BulkDownloadRequest,
    DocumentResponse,
    DocumentTypeUpdate,
    DuePaymentItem,
)
from app.schemas.document_versions import (
    DocumentVersionResponse,
    DocumentVersionListItem,
    SetCurrentVersionResponse,
)
from app.schemas.tags import (
    DocumentVersionTagsResponse,
    TagPoolCreateRequest,
    TagPoolCreateResponse,
    TagPoolResponse,
    TagUpdateRequest,
)
from app.processing.pipeline import process_document
from app.services.extraction.office import OFFICE_EXTENSIONS, is_valid_office_file
from app.storage.backends import build_object_storage_from_env

# from app.services.labelstudio.client import LabelStudioClient, LabelStudioConfig


router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_FILE_EXTENSIONS = {
    ".pdf",
    *OFFICE_EXTENSIONS,
    ".png",
    ".jpg",
    ".jpeg",
    ".tif",
    ".tiff",
    ".bmp",
    ".gif",
    ".webp",
}


def _validate_supported_upload(file: UploadFile, file_bytes: bytes) -> None:
    """Handle validate supported upload.

    Parameters:
        file (type=UploadFile): Uploaded file object provided by the request.
        file_bytes (type=bytes): Raw file content used for validation or processing.
    """
    filename = file.filename or ""
    suffix = Path(filename).suffix.lower()

    if suffix not in ALLOWED_FILE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: '{suffix or 'unknown'}'",
        )

    if suffix == ".pdf":
        if not file_bytes.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="File extension is .pdf but file content is not a valid PDF header",
            )
        return

    if suffix in OFFICE_EXTENSIONS:
        if not is_valid_office_file(file_bytes, filename):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Unsupported or invalid Office file",
            )
        return

    try:
        Image.open(io.BytesIO(file_bytes)).verify()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported or invalid image file",
        )


def _unique_zip_entry_name(raw_name: str, fallback: str, used_names: set[str]) -> str:
    """Return a safe, unique filename for a ZIP entry."""
    base_name = Path(raw_name or fallback).name or fallback
    stem = Path(base_name).stem or fallback
    suffix = Path(base_name).suffix
    candidate = base_name
    index = 2

    while candidate in used_names:
        candidate = f"{stem} ({index}){suffix}"
        index += 1

    used_names.add(candidate)
    return candidate


def _object_storage_enabled() -> bool:
    return os.getenv("OBJECT_STORAGE_ENABLED", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    # _=Depends(require_role("editor")),
    _=Depends(require_permission(Permissions.DOCUMENT_UPLOAD)),
):
    """Asynchronously handle upload document.

    Parameters:
        file (type=UploadFile, default=File(...)): Uploaded file object provided by the request.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
        _ (default=Depends(require_permission(Permissions.DOCUMENT_UPLOAD))): Dependency-injection placeholder argument required by FastAPI.
    """
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    _validate_supported_upload(file, file_bytes)

    storage_ref = None
    if _object_storage_enabled():
        try:
            storage = build_object_storage_from_env()
            object_key = f"documents/{uuid4()}/{file.filename or 'upload.bin'}"
            storage_ref = storage.put_bytes(
                bucket=os.getenv("OBJECT_STORAGE_BUCKET", "dms"),
                key=object_key,
                data=file_bytes,
                content_type=file.content_type or "application/octet-stream",
            )
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to store file in object storage: {exc}",
            ) from exc

    from app.services.hash import compute_content_hash

    content_hash = compute_content_hash(file_bytes)

    try:
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
            uploaded_by_user_id=current_user.id,
            commit=False,
        )

        version = create_document_version(
            db=db,
            document_id=document.id,
            file_bytes=None if storage_ref else file_bytes,
            set_as_current=True,
            storage_bucket=storage_ref.bucket if storage_ref else None,
            storage_key=storage_ref.key if storage_ref else None,
            storage_etag=storage_ref.etag if storage_ref else None,
            storage_size_bytes=storage_ref.size_bytes if storage_ref else None,
            commit=False,
        )

        process_document(
            db=db,
            version_id=version.id,
            file_bytes=file_bytes,
            commit=False,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        author=current_user.username,
        status=version.processing_status,
        document_type=document.document_type,
        confidence=version.confidence,
        created_at=document.created_at,
        current_version_id=version.id,
        tags=version.tags or [],
        due_date=version.due_date,
        size_bytes=version.storage_size_bytes,
        page_count=version.page_count,
    )


@router.get("/", response_model=list[DocumentResponse])
def get_documents(
    db: Session = Depends(get_db),
    # _=Depends(require_role("viewer")), #what if we comment out the viewing thing real quick one time
    _=Depends(require_permission(Permissions.DOCUMENT_READ)),
):
    """Return documents.

    Parameters:
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
        _ (default=Depends(require_permission(Permissions.DOCUMENT_READ))): Dependency-injection placeholder argument required by FastAPI.
    """
    rows = list_documents(db=db)

    return [
        DocumentResponse(
            id=doc.id,
            filename=doc.filename,
            author=uploader_username or "System",
            status=processing_status,
            document_type=doc.document_type or CLASSIFICATION,
            confidence=confidence,
            created_at=doc.created_at,
            current_version_id=doc.current_version_id,
            version_count=version_count or 1,
            current_version_number=current_version_number or 1,
            tags=tags or [],
            due_date=due_date,
            size_bytes=size_bytes,
            page_count=page_count,
        )
        for doc, processing_status, CLASSIFICATION, confidence, tags, due_date, page_count, size_bytes, uploader_username, version_count, current_version_number in rows
    ]


@router.get("/tag-pool", response_model=TagPoolResponse)
def get_tag_pool(
    q: str | None = None,
    db: Session = Depends(get_db),
    _=Depends(require_permission(Permissions.DOCUMENT_TAG_READ)),
):
    """Return tag pool.

    Parameters:
        q (type=str | None, default=None): Function argument used by this operation.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
        _ (default=Depends(require_permission(Permissions.DOCUMENT_TAG_READ))): Dependency-injection placeholder argument required by FastAPI.
    """
    pool = set(list_tag_pool(db=db, query=q))
    # Include tags already present on document versions as part of selectable pool.
    pool.update(list_existing_tags(db=db))
    return TagPoolResponse(tags=sorted(pool))


@router.post(
    "/tag-pool",
    response_model=TagPoolCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_tag_pool(
    payload: TagPoolCreateRequest,
    db: Session = Depends(get_db),
    _=Depends(require_permission(Permissions.DOCUMENT_TAG_EDIT)),
):
    """Create tag pool.

    Parameters:
        payload (type=TagPoolCreateRequest): Request payload containing client-provided input values.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
        _ (default=Depends(require_permission(Permissions.DOCUMENT_TAG_EDIT))): Dependency-injection placeholder argument required by FastAPI.
    """
    try:
        created = create_tag_pool_entry(db=db, tag=payload.tag)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return TagPoolCreateResponse(tag=created)


@router.post("/bulk-download")
def bulk_download_documents(
    payload: BulkDownloadRequest,
    db: Session = Depends(get_db),
    _=Depends(require_permission(Permissions.DOCUMENT_DOWNLOAD)),
):
    """Download current versions of multiple documents as a single ZIP archive."""
    unique_ids: list[UUID] = []
    seen_ids: set[UUID] = set()
    for document_id in payload.document_ids:
        if document_id not in seen_ids:
            seen_ids.add(document_id)
            unique_ids.append(document_id)

    items: list[tuple[str, bytes]] = []
    for document_id in unique_ids:
        document = get_document_by_id(db=db, document_id=document_id)
        if not document:
            raise HTTPException(
                status_code=404, detail=f"Document not found: {document_id}"
            )

        version = get_document_version(db=db, document_id=document_id)
        if not version:
            raise HTTPException(
                status_code=404, detail=f"File not found for document: {document_id}"
            )
        content = load_document_version_bytes(db=db, version_id=version.id)
        items.append((document.filename or str(document_id), content))

    archive_file = tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b")
    used_names: set[str] = set()
    with zipfile.ZipFile(
        archive_file, mode="w", compression=zipfile.ZIP_DEFLATED
    ) as zip_file:
        for index, (filename, content) in enumerate(items, start=1):
            entry_name = _unique_zip_entry_name(
                raw_name=filename,
                fallback=f"document-{index}.bin",
                used_names=used_names,
            )
            zip_file.writestr(entry_name, content)

    archive_file.seek(0)

    def iter_archive():
        try:
            while True:
                chunk = archive_file.read(1024 * 1024)
                if not chunk:
                    break
                yield chunk
        finally:
            archive_file.close()

    archive_name = (
        f"documents-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.zip"
    )
    return StreamingResponse(
        iter_archive(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{archive_name}"'},
    )


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    # _=Depends(require_role("viewer")),
    _=Depends(require_permission(Permissions.DOCUMENT_READ)),
):
    """Return document.

    Parameters:
        document_id (type=UUID): Identifier used to locate the target record.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
        _ (default=Depends(require_permission(Permissions.DOCUMENT_READ))): Dependency-injection placeholder argument required by FastAPI.
    """
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
        author=(
            document.uploaded_by_user.username
            if document.uploaded_by_user
            else "System"
        ),
        status=current_version.processing_status if current_version else None,
        document_type=document.document_type,
        confidence=current_version.confidence if current_version else None,
        created_at=document.created_at,
        current_version_id=document.current_version_id,
        version_count=len(versions) or 1,
        current_version_number=current_version_number or 1,
        tags=(current_version.tags if current_version else []) or [],
        due_date=current_version.due_date if current_version else None,
        size_bytes=current_version.storage_size_bytes if current_version else None,
        page_count=current_version.page_count if current_version else None,
    )


@router.patch("/{document_id}/type", response_model=DocumentResponse)
def set_document_type(
    document_id: UUID,
    payload: DocumentTypeUpdate,
    db: Session = Depends(get_db),
    # _=Depends(require_role("editor")),
    _=Depends(require_permission(Permissions.DOCUMENT_UPDATE)),
):
    """Set document type.

    Parameters:
        document_id (type=UUID): Identifier used to locate the target record.
        payload (type=DocumentTypeUpdate): Request payload containing client-provided input values.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
        _ (default=Depends(require_permission(Permissions.DOCUMENT_UPDATE))): Dependency-injection placeholder argument required by FastAPI.
    """
    document = update_document_type(
        db=db,
        document_id=document_id,
        document_type=payload.document_type,
    )

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    current_version = get_document_version(db=db, document_id=document_id)
    versions = list_document_versions(db=db, document_id=document_id)

    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        author=(
            document.uploaded_by_user.username
            if document.uploaded_by_user
            else "System"
        ),
        status=current_version.processing_status if current_version else None,
        document_type=document.document_type,
        confidence=current_version.confidence if current_version else None,
        created_at=document.created_at,
        current_version_id=document.current_version_id,
        version_count=len(versions) or 1,
        tags=(current_version.tags if current_version else []) or [],
        due_date=current_version.due_date if current_version else None,
        size_bytes=current_version.storage_size_bytes if current_version else None,
        page_count=current_version.page_count if current_version else None,
    )


@router.get("/{document_id}/output", response_model=DocumentVersionResponse)
def get_document_output(
    document_id: UUID,
    db: Session = Depends(get_db),
    # _=Depends(require_role("viewer")),
    _=Depends(require_permission(Permissions.DOCUMENT_READ)),
):
    """Return document output.

    Parameters:
        document_id (type=UUID): Identifier used to locate the target record.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
        _ (default=Depends(require_permission(Permissions.DOCUMENT_READ))): Dependency-injection placeholder argument required by FastAPI.
    """
    version = get_document_version(db=db, document_id=document_id)
    if not version:
        raise HTTPException(status_code=404, detail="No processed version available")
    return version


@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    # _=Depends(require_role("admin")),
    _=Depends(require_permission(Permissions.DOCUMENT_DELETE)),
):
    """Delete document.

    Parameters:
        document_id (type=UUID): Identifier used to locate the target record.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
        _ (default=Depends(require_permission(Permissions.DOCUMENT_DELETE))): Dependency-injection placeholder argument required by FastAPI.
    """
    document = get_document_by_id(db=db, document_id=document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    delete_document_repo(db=db, document_id=document_id)


@router.get("/{document_id}/download")
def download_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    # _=Depends(require_role("viewer")),
    _=Depends(require_permission(Permissions.DOCUMENT_DOWNLOAD)),
):
    """Handle download document.

    Parameters:
        document_id (type=UUID): Identifier used to locate the target record.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
        _ (default=Depends(require_permission(Permissions.DOCUMENT_DOWNLOAD))): Dependency-injection placeholder argument required by FastAPI.
    """
    version = get_document_version(db=db, document_id=document_id)
    if not version:
        raise HTTPException(status_code=404, detail="File not found")

    content = load_document_version_bytes(db=db, version_id=version.id)
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{version.document.filename}"'
        },
    )


@router.get("/{document_id}/preview")
def preview_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    _=Depends(require_permission(Permissions.DOCUMENT_PREVIEW)),
):
    """Handle preview document.

    Parameters:
        document_id (type=UUID): Identifier used to locate the target record.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
        _ (default=Depends(require_permission(Permissions.DOCUMENT_PREVIEW))): Dependency-injection placeholder argument required by FastAPI.
    """
    version = get_document_version(db=db, document_id=document_id)
    if not version:
        raise HTTPException(status_code=404, detail="File not found")

    filename = version.document.filename
    mime_type, _ = mimetypes.guess_type(filename)
    # force common previewable types
    if not mime_type:
        if filename.lower().endswith(".pdf"):
            mime_type = "application/pdf"
        elif filename.lower().endswith(".png"):
            mime_type = "image/png"
        elif filename.lower().endswith(".jpg") or filename.lower().endswith(".jpeg"):
            mime_type = "image/jpeg"
        else:
            mime_type = "application/octet-stream"

    content = load_document_version_bytes(db=db, version_id=version.id)
    return StreamingResponse(
        io.BytesIO(content),
        media_type=mime_type,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Content-Length": str(len(content)),
            "Cache-Control": "no-store",
        },
    )


@router.get("/{document_id}/versions", response_model=list[DocumentVersionListItem])
def get_document_versions(
    document_id: UUID,
    db: Session = Depends(get_db),
    _=Depends(require_permission(Permissions.DOCUMENT_VERSION_READ)),
):
    """Return document versions.

    Parameters:
        document_id (type=UUID): Identifier used to locate the target record.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
        _ (default=Depends(require_permission(Permissions.DOCUMENT_VERSION_READ))): Dependency-injection placeholder argument required by FastAPI.
    """
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
            ocr_engine=version.ocr_engine,
            ocr_model_version=version.ocr_model_version,
            tags=version.tags or [],
            created_at=version.created_at,
            size_bytes=version.storage_size_bytes
            or (len(version.content) if version.content else 0),
            due_date=version.due_date,
            page_count=version.page_count,
        )
        for index, version in enumerate(versions)
    ]


@router.get("/upcoming-due-payments", response_model=list[DuePaymentItem])
def get_upcoming_due_payments(
    days_ahead: int = 30,
    limit: int = 50,
    db: Session = Depends(get_db),
    _=Depends(require_permission(Permissions.DOCUMENT_DUE_PAYMENTS)),
):
    """Return upcoming due payments for incoming invoices."""
    if days_ahead < 0:
        raise HTTPException(status_code=400, detail="days_ahead must be >= 0")
    if limit <= 0:
        raise HTTPException(status_code=400, detail="limit must be > 0")

    start = date.today()
    end = start + timedelta(days=days_ahead)

    rows = list_upcoming_due_payments(
        db=db,
        start_date=start,
        end_date=end,
        limit=min(limit, 200),
    )

    return [
        DuePaymentItem(
            document_id=doc.id,
            version_id=version.id,
            filename=doc.filename,
            due_date=version.due_date,
        )
        for doc, version in rows
        if version.due_date is not None
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
    """Create new document version.

    Parameters:
        document_id (type=UUID): Identifier used to locate the target record.
        file (type=UploadFile, default=File(...)): Uploaded file object provided by the request.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
        _ (default=Depends(require_permission(Permissions.DOCUMENT_VERSION_CREATE))): Dependency-injection placeholder argument required by FastAPI.
    """
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    _validate_supported_upload(file, file_bytes)

    document = get_document_by_id(db=db, document_id=document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    storage_ref = None
    if _object_storage_enabled():
        try:
            storage = build_object_storage_from_env()
            object_key = f"documents/{uuid4()}/{file.filename or 'upload.bin'}"
            storage_ref = storage.put_bytes(
                bucket=os.getenv("OBJECT_STORAGE_BUCKET", "dms"),
                key=object_key,
                data=file_bytes,
                content_type=file.content_type or "application/octet-stream",
            )
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to store file in object storage: {exc}",
            ) from exc

    try:
        version = create_document_version(
            db=db,
            document_id=document_id,
            file_bytes=None if storage_ref else file_bytes,
            set_as_current=True,
            storage_bucket=storage_ref.bucket if storage_ref else None,
            storage_key=storage_ref.key if storage_ref else None,
            storage_etag=storage_ref.etag if storage_ref else None,
            storage_size_bytes=storage_ref.size_bytes if storage_ref else None,
            commit=False,
        )

        if file.filename and not document.filename:
            document.filename = file.filename

        db.flush()

        process_document(
            db=db,
            version_id=version.id,
            file_bytes=file_bytes,
            commit=False,
        )

        db.commit()
        return version

    except Exception:
        db.rollback()
        raise


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
    """Set current version.

    Parameters:
        document_id (type=UUID): Identifier used to locate the target record.
        version_id (type=UUID): Identifier used to locate the target record.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
        _ (default=Depends(require_permission(Permissions.DOCUMENT_VERSION_SET_CURRENT))): Dependency-injection placeholder argument required by FastAPI.
    """
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
    """Handle download document version.

    Parameters:
        document_id (type=UUID): Identifier used to locate the target record.
        version_id (type=UUID): Identifier used to locate the target record.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
        _ (default=Depends(require_permission(Permissions.DOCUMENT_VERSION_DOWNLOAD))): Dependency-injection placeholder argument required by FastAPI.
    """
    version = get_document_version_by_id(db=db, version_id=version_id)
    if not version or version.document_id != document_id:
        raise HTTPException(status_code=404, detail="File version not found")

    content = load_document_version_bytes(db=db, version_id=version.id)
    return StreamingResponse(
        io.BytesIO(content),
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
    """Handle preview document version.

    Parameters:
        document_id (type=UUID): Identifier used to locate the target record.
        version_id (type=UUID): Identifier used to locate the target record.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
        _ (default=Depends(require_permission(Permissions.DOCUMENT_VERSION_PREVIEW))): Dependency-injection placeholder argument required by FastAPI.
    """
    version = get_document_version_by_id(db=db, version_id=version_id)
    if not version or version.document_id != document_id:
        raise HTTPException(status_code=404, detail="File version not found")

    filename = version.document.filename
    mime_type, _ = mimetypes.guess_type(filename)
    mime_type = mime_type or "application/octet-stream"

    content = load_document_version_bytes(db=db, version_id=version.id)
    return StreamingResponse(
        io.BytesIO(content),
        media_type=mime_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.get(
    "/{document_id}/versions/{version_id}/tags",
    response_model=DocumentVersionTagsResponse,
)
def get_document_version_tags(
    document_id: UUID,
    version_id: UUID,
    db: Session = Depends(get_db),
    _=Depends(require_permission(Permissions.DOCUMENT_TAG_READ)),
):
    """Return document version tags.

    Parameters:
        document_id (type=UUID): Identifier used to locate the target record.
        version_id (type=UUID): Identifier used to locate the target record.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
        _ (default=Depends(require_permission(Permissions.DOCUMENT_TAG_READ))): Dependency-injection placeholder argument required by FastAPI.
    """
    version = get_document_version_by_id(db=db, version_id=version_id)
    if not version or version.document_id != document_id:
        raise HTTPException(status_code=404, detail="Document version not found")

    return DocumentVersionTagsResponse(
        document_id=document_id,
        version_id=version_id,
        tags=version.tags or [],
    )


@router.put(
    "/{document_id}/versions/{version_id}/tags",
    response_model=DocumentVersionTagsResponse,
)
def replace_tags_on_document_version(
    document_id: UUID,
    version_id: UUID,
    payload: TagUpdateRequest,
    db: Session = Depends(get_db),
    _=Depends(require_permission(Permissions.DOCUMENT_TAG_EDIT)),
):
    """Handle replace tags on document version.

    Parameters:
        document_id (type=UUID): Identifier used to locate the target record.
        version_id (type=UUID): Identifier used to locate the target record.
        payload (type=TagUpdateRequest): Request payload containing client-provided input values.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
        _ (default=Depends(require_permission(Permissions.DOCUMENT_TAG_EDIT))): Dependency-injection placeholder argument required by FastAPI.
    """
    version = get_document_version_by_id(db=db, version_id=version_id)
    if not version or version.document_id != document_id:
        raise HTTPException(status_code=404, detail="Document version not found")

    tags = replace_document_version_tags(db=db, version=version, tags=payload.tags)
    return DocumentVersionTagsResponse(
        document_id=document_id,
        version_id=version_id,
        tags=tags,
    )


@router.post(
    "/{document_id}/versions/{version_id}/tags/add",
    response_model=DocumentVersionTagsResponse,
)
def add_tags_to_document_version(
    document_id: UUID,
    version_id: UUID,
    payload: TagUpdateRequest,
    db: Session = Depends(get_db),
    _=Depends(require_permission(Permissions.DOCUMENT_TAG_EDIT)),
):
    """Add tags to document version.

    Parameters:
        document_id (type=UUID): Identifier used to locate the target record.
        version_id (type=UUID): Identifier used to locate the target record.
        payload (type=TagUpdateRequest): Request payload containing client-provided input values.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
        _ (default=Depends(require_permission(Permissions.DOCUMENT_TAG_EDIT))): Dependency-injection placeholder argument required by FastAPI.
    """
    version = get_document_version_by_id(db=db, version_id=version_id)
    if not version or version.document_id != document_id:
        raise HTTPException(status_code=404, detail="Document version not found")

    tags = add_document_version_tags(db=db, version=version, tags=payload.tags)
    return DocumentVersionTagsResponse(
        document_id=document_id,
        version_id=version_id,
        tags=tags,
    )


@router.post(
    "/{document_id}/versions/{version_id}/tags/remove",
    response_model=DocumentVersionTagsResponse,
)
def remove_tags_from_document_version(
    document_id: UUID,
    version_id: UUID,
    payload: TagUpdateRequest,
    db: Session = Depends(get_db),
    _=Depends(require_permission(Permissions.DOCUMENT_TAG_EDIT)),
):
    """Remove tags from document version.

    Parameters:
        document_id (type=UUID): Identifier used to locate the target record.
        version_id (type=UUID): Identifier used to locate the target record.
        payload (type=TagUpdateRequest): Request payload containing client-provided input values.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
        _ (default=Depends(require_permission(Permissions.DOCUMENT_TAG_EDIT))): Dependency-injection placeholder argument required by FastAPI.
    """
    version = get_document_version_by_id(db=db, version_id=version_id)
    if not version or version.document_id != document_id:
        raise HTTPException(status_code=404, detail="Document version not found")

    tags = remove_document_version_tags(db=db, version=version, tags=payload.tags)
    return DocumentVersionTagsResponse(
        document_id=document_id,
        version_id=version_id,
        tags=tags,
    )
