from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from datetime import date
import uuid
from uuid import UUID

from app.db.models import Document, DocumentVersion
from app.db.models.documents import DocumentType
from app.db.models.user import User
from app.db.models.enums import ProcessingStatus, DocumentClass
from app.services.extraction.tags import normalize_tag


def create_document(
    db: Session,
    filename: str,
    content_hash: str,
    uploaded_by_user_id: UUID | None = None,
    *,
    commit: bool = True,
) -> Document:
    """Create document.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        filename (type=str): File or entity name used for storage and display.
        content_hash (type=str): Function argument used by this operation.
        commit (type=bool, default=True): Flag controlling whether to commit the transaction.
    """
    document = Document(
        id=uuid.uuid4(),
        filename=filename,
        content_hash=content_hash,
        uploaded_by_user_id=uploaded_by_user_id,
    )
    db.add(document)
    if commit:
        db.commit()
        db.refresh(document)
    else:
        db.flush()
    return document


def create_document_version(
    db: Session,
    document_id: UUID,
    file_bytes: bytes | None,
    set_as_current: bool = False,
    *,
    storage_bucket: str | None = None,
    storage_key: str | None = None,
    storage_etag: str | None = None,
    storage_size_bytes: int | None = None,
    commit: bool = True,
) -> DocumentVersion:
    """Create document version.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        document_id (type=UUID): Identifier used to locate the target record.
        file_bytes (type=bytes | None): Raw file content used for validation or processing.
        storage_bucket (type=str | None): Object storage bucket name.
        storage_key (type=str | None): Object storage key.
        storage_etag (type=str | None): Object storage ETag (if available).
        storage_size_bytes (type=int | None): Object storage size in bytes.
        set_as_current (type=bool, default=False): Function argument used by this operation.
        commit (type=bool, default=True): Flag controlling whether to commit the transaction.
    """
    if file_bytes is None and not storage_key:
        raise ValueError("file_bytes or storage_key is required to create a document version")

    version = DocumentVersion(
        id=uuid.uuid4(),
        document_id=document_id,
        content=file_bytes,
        storage_bucket=storage_bucket,
        storage_key=storage_key,
        storage_etag=storage_etag,
        storage_size_bytes=storage_size_bytes or (len(file_bytes) if file_bytes is not None else None),
        processing_status=ProcessingStatus.uploaded,
    )
    db.add(version)
    if commit:
        db.commit()
        db.refresh(version)
    else:
        db.flush()
    
    document = db.get(Document, document_id)
    if document and (set_as_current or not document.current_version_id):
        document.current_version_id = version.id
        if commit:
            db.commit()
            db.refresh(document)
        else:
            db.flush()
        
    return version


def load_document_version_bytes(
    db: Session,
    version_id: UUID,
) -> bytes:
    """Handle load document version bytes.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        version_id (type=UUID): Identifier used to locate the target record.
    """
    version = db.get(DocumentVersion, version_id)

    if not version:
        raise ValueError("DocumentVersion not found")

    if version.storage_key:
        from app.storage.backends import build_object_storage_from_env

        storage = build_object_storage_from_env()
        bucket = version.storage_bucket or "dms"
        return storage.get_bytes(bucket=bucket, key=version.storage_key)

    if version.content is None:
        raise ValueError("DocumentVersion has no content stored")

    return version.content


def update_processing_results(
    db: Session,
    version_id: UUID,
    extracted_text: str,
    classification,
    confidence: float,
    tags: list[str] | None = None,
    due_date: date | None = None,
    page_count: int | None = None,
    ocr_raw_confidence: float | None = None,
    ocr_engine: str | None = None,
    ocr_model_version: str | None = None,
    ocr_latency_ms: int | None = None,
):
    """Update processing results.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        version_id (type=UUID): Identifier used to locate the target record.
        extracted_text (type=str): Function argument used by this operation.
        classification: Function argument used by this operation.
        confidence (type=float): Function argument used by this operation.
        tags (type=list[str] | None, default=None): Function argument used by this operation.
        ocr_raw_confidence (type=float | None, default=None): Function argument used by this operation.
        ocr_engine (type=str | None, default=None): Function argument used by this operation.
        ocr_model_version (type=str | None, default=None): Function argument used by this operation.
        ocr_latency_ms (type=int | None, default=None): Function argument used by this operation.
    """
    version = db.get(DocumentVersion, version_id)

    if not version:
        raise ValueError("DocumentVersion not found")

    version.extracted_text = extracted_text
    version.classification = classification
    version.confidence = confidence
    version.tags = tags or []
    version.ocr_raw_confidence = ocr_raw_confidence
    version.ocr_engine = ocr_engine
    version.ocr_model_version = ocr_model_version
    version.ocr_latency_ms = ocr_latency_ms
    version.due_date = due_date
    version.page_count = page_count
    version.processing_status = ProcessingStatus.uploaded

    db.commit()


def get_document_by_hash(
    db: Session,
    content_hash: str,
) -> Document | None:
    """Return document by hash.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        content_hash (type=str): Function argument used by this operation.
    """
    return (
        db.query(Document)
        .filter(Document.content_hash == content_hash)
        .one_or_none()
    )


def get_document_by_id(
    db: Session,
    document_id: UUID,
) -> Document | None:
    """Return document by id.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        document_id (type=UUID): Identifier used to locate the target record.
    """
    return db.get(Document, document_id)


def get_document(
    db: Session,
    document_id: UUID,
) -> Document | None:
    """Return document.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        document_id (type=UUID): Identifier used to locate the target record.
    """
    return get_document_by_id(db, document_id)


def list_documents(db: Session):
    """Return documents.

    Parameters:
        db (type=Session): Database session used for persistence operations.
    """
    rows = (
        db.query(
            Document,
            DocumentVersion.processing_status,
            DocumentVersion.classification,
            DocumentVersion.confidence,
            DocumentVersion.tags,
            DocumentVersion.due_date,
            DocumentVersion.page_count,
            DocumentVersion.storage_size_bytes,
            User.username,
        )
        .outerjoin(
            DocumentVersion,
            Document.current_version_id == DocumentVersion.id,
        )
        .outerjoin(
            User,
            Document.uploaded_by_user_id == User.id,
        )
        .order_by(Document.created_at.desc())
        .all()
    )

    document_ids = [doc.id for doc, *_ in rows]
    if not document_ids:
        return []

    versions = (
        db.query(DocumentVersion.document_id, DocumentVersion.id)
        .filter(DocumentVersion.document_id.in_(document_ids))
        .order_by(DocumentVersion.document_id.asc(), DocumentVersion.created_at.asc())
        .all()
    )

    version_ids_by_document: dict[UUID, list[UUID]] = {}
    for document_id, version_id in versions:
        version_ids_by_document.setdefault(document_id, []).append(version_id)

    return [
        (
            doc,
            processing_status,
            classification,
            confidence,
            tags,
            due_date,
            page_count,
            size_bytes,
            uploader_username,
            len(version_ids_by_document.get(doc.id, [])),
            (
                version_ids_by_document.get(doc.id, []).index(doc.current_version_id) + 1
                if doc.current_version_id and doc.current_version_id in version_ids_by_document.get(doc.id, [])
                else None
            ),
        )
        for doc, processing_status, classification, confidence, tags, due_date, page_count, size_bytes, uploader_username in rows
    ]


def update_document_type(
    db: Session,
    document_id: UUID,
    document_type: str,
) -> Document | None:
    """Update document type.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        document_id (type=UUID): Identifier used to locate the target record.
        document_type (type=str): Function argument used by this operation.
    """
    document = db.get(Document, document_id)

    if not document:
        return None

    document.document_type = document_type
    db.commit()
    db.refresh(document)

    return document


def get_document_version(
    db: Session,
    document_id: UUID,
) -> DocumentVersion | None:
    """Return document version.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        document_id (type=UUID): Identifier used to locate the target record.
    """
    document = db.get(Document, document_id)

    if not document or not document.current_version_id:
        return None

    return db.get(DocumentVersion, document.current_version_id)


def get_document_version_by_id(
    db: Session,
    version_id: UUID,
) -> DocumentVersion | None:
    """Return document version by id.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        version_id (type=UUID): Identifier used to locate the target record.
    """
    return db.get(DocumentVersion, version_id)


def reset_processing_state(
    db: Session,
    version_id: UUID,
) -> DocumentVersion | None:
    """Reset processing fields for a version before reprocessing.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        version_id (type=UUID): Identifier used to locate the target record.
    """
    version = db.get(DocumentVersion, version_id)
    if not version:
        return None

    version.extracted_text = None
    version.classification = None
    version.confidence = None
    version.ocr_raw_confidence = None
    version.ocr_engine = None
    version.ocr_model_version = None
    version.ocr_latency_ms = None
    version.tags = []
    version.due_date = None
    version.page_count = None
    version.processing_status = ProcessingStatus.pending
    db.commit()
    db.refresh(version)
    return version


def list_upcoming_due_payments(
    db: Session,
    *,
    start_date: date,
    end_date: date,
    limit: int = 50,
) -> list[tuple[Document, DocumentVersion]]:
    """Return upcoming due payments for incoming invoices."""
    rows = (
        db.query(Document, DocumentVersion)
        .join(DocumentVersion, Document.current_version_id == DocumentVersion.id)
        .filter(
            DocumentVersion.due_date.isnot(None),
            DocumentVersion.due_date >= start_date,
            DocumentVersion.due_date <= end_date,
            or_(
                Document.document_type == DocumentType.incoming_invoice,
                DocumentVersion.classification == DocumentClass.INCOMING_INVOICE,
            ),
        )
        .order_by(DocumentVersion.due_date.asc(), Document.created_at.asc())
        .limit(limit)
        .all()
    )
    return rows


def list_existing_tags(
    db: Session,
) -> list[str]:
    """Return existing tags.

    Parameters:
        db (type=Session): Database session used for persistence operations.
    """
    rows = db.query(DocumentVersion.tags).filter(DocumentVersion.tags.isnot(None)).all()
    values: set[str] = set()
    for (tags,) in rows:
        if not tags:
            continue
        for tag in tags:
            if isinstance(tag, str):
                normalized = normalize_tag(tag)
                if normalized:
                    values.add(normalized)
    return sorted(values)


def replace_document_version_tags(
    db: Session,
    version: DocumentVersion,
    tags: list[str],
) -> list[str]:
    """Handle replace document version tags.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        version (type=DocumentVersion): Function argument used by this operation.
        tags (type=list[str]): Function argument used by this operation.
    """
    normalized = sorted({t for t in (normalize_tag(tag) for tag in tags) if t})
    version.tags = normalized
    db.commit()
    db.refresh(version)
    return version.tags or []


def add_document_version_tags(
    db: Session,
    version: DocumentVersion,
    tags: list[str],
) -> list[str]:
    """Add document version tags.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        version (type=DocumentVersion): Function argument used by this operation.
        tags (type=list[str]): Function argument used by this operation.
    """
    existing = set(version.tags or [])
    for tag in tags:
        normalized = normalize_tag(tag)
        if normalized:
            existing.add(normalized)
    version.tags = sorted(existing)
    db.commit()
    db.refresh(version)
    return version.tags or []


def remove_document_version_tags(
    db: Session,
    version: DocumentVersion,
    tags: list[str],
) -> list[str]:
    """Remove document version tags.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        version (type=DocumentVersion): Function argument used by this operation.
        tags (type=list[str]): Function argument used by this operation.
    """
    remove = {t for t in (normalize_tag(tag) for tag in tags) if t}
    current = set(version.tags or [])
    version.tags = sorted(current - remove)
    db.commit()
    db.refresh(version)
    return version.tags or []


def list_document_versions(
    db: Session,
    document_id: UUID,
) -> list[DocumentVersion]:
    """Return document versions.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        document_id (type=UUID): Identifier used to locate the target record.
    """
    return (
        db.query(DocumentVersion)
        .filter(DocumentVersion.document_id == document_id)
        .order_by(DocumentVersion.created_at.asc())
        .all()
    )


def set_current_document_version(
    db: Session,
    document: Document,
    version: DocumentVersion,
) -> None:
    """Set current document version.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        document (type=Document): Function argument used by this operation.
        version (type=DocumentVersion): Function argument used by this operation.
    """
    document.current_version_id = version.id
    db.commit()
    db.refresh(document)


def delete_document(
    db: Session,
    document_id: UUID,
) -> None:
    """Deletes a document and all its versions.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        document_id (type=UUID): Identifier used to locate the target record.
    """
    document = db.get(Document, document_id)
    if not document:
        raise ValueError(f"Document {document_id} not found")

    # Delete all versions associated with this document
    versions = db.query(DocumentVersion).filter(DocumentVersion.document_id == document_id).all()
    for v in versions:
        db.delete(v)

    # Delete the document itself
    db.delete(document)
    db.commit()
