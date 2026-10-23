from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, func
from datetime import date
import uuid
from uuid import UUID

from app.db.models import Document, DocumentVersion
from app.db.models.tag_catalog import TagCatalog
from app.db.models.user import User
from app.db.models.training_feedback_event import TrainingFeedbackEvent
from app.db.models.enums import ProcessingStatus
from app.db.models.ocr_correction import CorrectionStatus, OCRCorrectionQueue, OCRWordBox
from app.services.extraction.tags import normalize_tag


def _user_passes_security_clearance(user: User | None, tags: list[str] | None) -> bool:
    """Return True if the user has the required role for any security_clearance tags."""
    if not tags:
        return True
    clearance_tags = [
        tag
        for tag in tags
        if isinstance(tag, str) and tag.lower().startswith("security_clearance:")
    ]
    if not clearance_tags:
        return True
    if user is None:
        return False
    user_roles = {role.name.lower() for role in (user.roles or [])}
    for tag in clearance_tags:
        required = tag.split(":", 1)[1].strip().lower()
        if required not in user_roles:
            return False
    return True


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
    created_by_user_id: UUID | None = None,
    set_as_current: bool = False,
    *,
    storage_bucket: str | None = None,
    storage_key: str | None = None,
    storage_etag: str | None = None,
    storage_size_bytes: int | None = None,
    content_hash: str | None = None,
    layout_json: dict | None = None,
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
        created_by_user_id (type=UUID | None): User id of the person creating the version.
        layout_json (type=dict | None): Optional annotation metadata to associate with the version.
        set_as_current (type=bool, default=False): Function argument used by this operation.
        commit (type=bool, default=True): Flag controlling whether to commit the transaction.
    """
    if file_bytes is None and not storage_key:
        raise ValueError(
            "file_bytes or storage_key is required to create a document version"
        )

    document = db.get(Document, document_id)
    if not document:
        raise ValueError("Document not found")

    # version number is incremented based on the latest existing version for this document, not based on filename or storage key
    latest = (
        db.query(DocumentVersion.version_number)
        .filter(DocumentVersion.document_id == document_id)
        .order_by(DocumentVersion.version_number.desc())
        .first()
    )

    version_number = (latest[0] if latest else 0) + 1

    version = DocumentVersion(
        id=uuid.uuid4(),
        document_id=document_id,
        content=file_bytes,
        storage_bucket=storage_bucket,
        storage_key=storage_key,
        storage_etag=storage_etag,
        storage_size_bytes=storage_size_bytes
        or (len(file_bytes) if file_bytes is not None else None),
        created_by_user_id=created_by_user_id,
        ocr_meta={"layout": layout_json} if layout_json is not None else None,
        content_hash=content_hash,
        version_number=version_number,
        processing_status=ProcessingStatus.processing,
    )

    db.add(version)
    db.flush()

    # update document pointer
    if set_as_current or not document.current_version_id:
        document.current_version_id = version.id

    if commit:
        db.commit()
        db.refresh(version)
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
    version.document.document_type = classification
    version.ocr_meta = {
        **(version.ocr_meta or {}),
        "confidence": confidence,
        "raw_confidence": ocr_raw_confidence,
        "engine": ocr_engine,
        "model_version": ocr_model_version,
        "latency_ms": ocr_latency_ms,
    }
    version.document.label_tags = tags or []
    version.document.due_date = due_date
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
        .join(DocumentVersion, DocumentVersion.document_id == Document.id)
        .filter(DocumentVersion.content_hash == content_hash)
        .order_by(DocumentVersion.created_at.desc())
        .first()
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


def list_documents(
    db: Session, query: str | None = None, current_user: User | None = None
):
    """Return documents.

    Parameters:
        db (type=Session): Database session used for persistence operations.
    """
    rows_query = (
        db.query(Document, DocumentVersion, func.coalesce(User.full_name, User.username))
        .outerjoin(DocumentVersion, Document.current_version_id == DocumentVersion.id)
        .outerjoin(User, Document.uploaded_by_user_id == User.id)
    )
    search = (query or "").strip()
    if search:
        pattern = f"%{search.lower()}%"
        rows_query = rows_query.filter(or_(
            func.lower(Document.filename).like(pattern),
            func.lower(User.username).like(pattern),
            func.lower(func.coalesce(User.full_name, "")).like(pattern),
            func.lower(func.coalesce(DocumentVersion.extracted_text, "")).like(pattern),
        ))
    rows = rows_query.order_by(Document.created_at.desc()).all()
    ids = [doc.id for doc, _, _ in rows]
    version_rows = (db.query(DocumentVersion.document_id, DocumentVersion.id)
                    .filter(DocumentVersion.document_id.in_(ids))
                    .order_by(DocumentVersion.document_id, DocumentVersion.created_at).all()) if ids else []
    ids_by_doc: dict[UUID, list[UUID]] = {}
    for did, vid in version_rows:
        ids_by_doc.setdefault(did, []).append(vid)
    result = []
    for doc, version, uploader in rows:
        labels = [tag.name for tag in (doc.tags or []) if tag.kind == "label"]
        if not _user_passes_security_clearance(current_user, labels):
            continue
        ids_for_doc = ids_by_doc.get(doc.id, [])
        result.append((doc, version.processing_status if version else None,
                       doc.document_type, (version.ocr_meta or {}).get("confidence") if version else None,
                       labels, doc.due_date, version.page_count if version else None,
                       version.storage_size_bytes if version else None, doc.workflow_notes,
                       uploader, len(ids_for_doc),
                       ids_for_doc.index(doc.current_version_id) + 1 if doc.current_version_id in ids_for_doc else None))
    return result


def set_document_type(db: Session, document_id: UUID, tag_id: UUID) -> Document | None:
    document = db.get(Document, document_id)
    tag = db.get(TagCatalog, tag_id)
    if not document:
        return None
    if not tag or tag.kind != "document_type":
        raise ValueError("Tag must exist and have kind='document_type'")
    document.document_type_tag = tag
    db.commit()
    db.refresh(document)
    return document


def clear_document_type(db: Session, document_id: UUID) -> Document | None:
    document = db.get(Document, document_id)
    if not document:
        return None
    document.document_type_tag = None
    db.commit()
    db.refresh(document)
    return document


def update_document_type(db: Session, document_id: UUID, document_type: str) -> Document | None:
    document = db.get(Document, document_id)
    if not document:
        return None
    name = str(getattr(document_type, "value", document_type)).lower()
    tag = db.query(TagCatalog).filter_by(name=name, kind="document_type").one_or_none()
    if not tag:
        raise ValueError("Unknown document_type tag")
    document.document_type_tag = tag
    db.commit()
    db.refresh(document)
    return document


def add_tag(db: Session, document_id: UUID, tag_id: UUID) -> list[str]:
    document = db.get(Document, document_id)
    tag = db.get(TagCatalog, tag_id)
    if not document:
        raise ValueError("Document not found")
    if not tag or tag.kind != "label":
        raise ValueError("Tag must exist and have kind='label'")
    if tag not in document.tags:
        document.tags.append(tag)
    db.commit()
    return sorted(t.name for t in document.tags if t.kind == "label")


def remove_tag(db: Session, document_id: UUID, tag_id: UUID) -> list[str]:
    document = db.get(Document, document_id)
    tag = db.get(TagCatalog, tag_id)
    if not document:
        raise ValueError("Document not found")
    if not tag or tag.kind != "label":
        raise ValueError("Tag must exist and have kind='label'")
    document.tags = [t for t in document.tags if t.id != tag.id]
    db.commit()
    return sorted(t.name for t in document.tags if t.kind == "label")


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

    # Reprocessing produces a fresh extraction. Clear the previous values so
    # the UI cannot present stale OCR output while the worker is running.
    version.extracted_text = None
    version.extraction = None
    version.extraction_raw = None
    version.ocr_meta = None
    version.page_count = None
    version.processing_status = ProcessingStatus.processing

    document = version.document
    document.data = {}
    document.document_type_tag = None
    document.label_tags = []
    document.due_date = None

    # Word boxes belong to this OCR run. Keep field correction rows as audit
    # history, but remove obsolete OCR evidence.
    db.query(OCRWordBox).filter(
        OCRWordBox.document_version_id == version.id
    ).delete(synchronize_session=False)

    # A confirmed correction applies to the old extraction. Require review of
    # the new OCR result after reprocessing, while preserving the queue row.
    queue_item = db.query(OCRCorrectionQueue).filter_by(
        document_version_id=version.id
    ).one_or_none()
    if queue_item:
        queue_item.status = CorrectionStatus.pending
        queue_item.confirmed_at = None
        queue_item.confirmed_by = None

    db.commit()
    db.refresh(version)
    return version


def update_document_workflow(
    db: Session,
    document_id: UUID,
    status: ProcessingStatus,
    notes: str | None,
) -> DocumentVersion | None:
    version = get_document_version(db=db, document_id=document_id)
    if not version:
        return None
    version.processing_status = status.value
    version.document.workflow_notes = notes.strip() if notes else None
    db.commit()
    db.refresh(version)
    return version


def list_upcoming_due_payments(
    db: Session,
    *,
    start_date: date,
    end_date: date,
    limit: int | None = None,
) -> list[tuple[Document, DocumentVersion]]:
    """Return current document versions with a due date in the requested window."""
    query = (
        db.query(Document, DocumentVersion)
        .join(DocumentVersion, Document.current_version_id == DocumentVersion.id)
        .filter(
            Document.due_date.isnot(None),
            Document.due_date >= start_date,
            Document.due_date <= end_date,
        )
        .order_by(Document.due_date.asc(), Document.created_at.asc())
    )
    if limit is not None:
        query = query.limit(limit)
    return query.all()


def list_existing_tags(
    db: Session,
) -> list[str]:
    """Return existing tags.

    Parameters:
        db (type=Session): Database session used for persistence operations.
    """
    rows = db.query(TagCatalog).filter(
        TagCatalog.kind == "label",
        ~TagCatalog.name.like("due_date:%"),
        ~TagCatalog.name.like("payment_due_date:%"),
    ).order_by(TagCatalog.name).all()
    return [row.name for row in rows]


def list_rejected_tags(
    db: Session,
    *,
    min_count: int = 1,
) -> list[str]:
    """Return tags users have removed from AI suggestions."""
    removal_counts: dict[str, int] = {}
    events = (
        db.query(TrainingFeedbackEvent.predicted_tags, TrainingFeedbackEvent.final_tags)
        .filter(TrainingFeedbackEvent.event_type == "tags_remove")
        .filter(TrainingFeedbackEvent.include_in_training.is_(True))
        .all()
    )

    for predicted_tags, final_tags in events:
        predicted: set[str] = set()
        final: set[str] = set()

        for tag in predicted_tags or []:
            if isinstance(tag, str):
                normalized = normalize_tag(tag)
                if normalized:
                    predicted.add(normalized)

        for tag in final_tags or []:
            if isinstance(tag, str):
                normalized = normalize_tag(tag)
                if normalized:
                    final.add(normalized)

        for tag in predicted - final:
            removal_counts[tag] = removal_counts.get(tag, 0) + 1

    return sorted(tag for tag, count in removal_counts.items() if count >= min_count)


def replace_document_version_tags(db: Session, version: DocumentVersion, tags: list[str]) -> list[str]:
    document = version.document
    normalized = sorted({
        t for t in (normalize_tag(tag) for tag in tags)
        if t and not t.startswith(("due_date:", "payment_due_date:"))
    })
    rows = []
    for name in normalized:
        row = db.query(TagCatalog).filter_by(name=name).one_or_none()
        if row is None:
            row = TagCatalog(name=name, kind="label")
            db.add(row)
            db.flush()
        if row.kind != "label":
            continue
        rows.append(row)
    document.tags = [t for t in document.tags if t.kind != "label"] + rows
    db.commit()
    return sorted(t.name for t in document.tags if t.kind == "label")


def add_document_version_tags(db: Session, version: DocumentVersion, tags: list[str]) -> list[str]:
    current = set(version.document.label_tags or [])
    current.update(
        t for t in (normalize_tag(tag) for tag in tags)
        if t and not t.startswith(("due_date:", "payment_due_date:"))
    )
    return replace_document_version_tags(db, version, sorted(current))


def remove_document_version_tags(db: Session, version: DocumentVersion, tags: list[str]) -> list[str]:
    remove = {t for t in (normalize_tag(tag) for tag in tags) if t}
    return replace_document_version_tags(db, version, sorted(set(version.document.label_tags or []) - remove))


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


def delete_document_version(
    db: Session,
    document: Document,
    version: DocumentVersion,
) -> None:
    """Delete one document version and maintain current version pointer."""
    versions = (
        db.query(DocumentVersion)
        .filter(DocumentVersion.document_id == document.id)
        .order_by(DocumentVersion.created_at.asc())
        .all()
    )
    if len(versions) <= 1:
        raise ValueError("Cannot delete the only version")

    replacement = None
    if document.current_version_id == version.id:
        remaining = [v for v in versions if v.id != version.id]
        replacement = remaining[-1] if remaining else None

    db.delete(version)
    db.flush()

    if replacement is not None:
        document.current_version_id = replacement.id

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
    versions = (
        db.query(DocumentVersion)
        .filter(DocumentVersion.document_id == document_id)
        .all()
    )
    for v in versions:
        db.delete(v)

    # Delete the document itself
    db.delete(document)
    db.commit()


def _get_next_version_number(db, document_id):
    max_version = (
        db.query(func.max(DocumentVersion.version_number))
        .filter(DocumentVersion.document_id == document_id)
        .scalar()
    )
    return (max_version or 0) + 1


def update_document_name(db: Session, document_id: UUID, name: str):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        return None
    document.filename = name.strip()
    db.commit()
    db.refresh(document)
    return document
