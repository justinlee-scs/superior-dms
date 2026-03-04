from sqlalchemy.orm import Session
from sqlalchemy import desc
import uuid
from uuid import UUID

from app.db.models import Document, DocumentVersion
from app.db.models.enums import ProcessingStatus
from app.services.extraction.tags import normalize_tag


def create_document(
    db: Session,
    filename: str,
    content_hash: str,
    *,
    commit: bool = True,
) -> Document:
    document = Document(
        id=uuid.uuid4(),
        filename=filename,
        content_hash=content_hash,
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
    file_bytes: bytes,
    set_as_current: bool = False,
    *,
    commit: bool = True,
) -> DocumentVersion:
    version = DocumentVersion(
        id=uuid.uuid4(),
        document_id=document_id,
        content=file_bytes,
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
    version = db.get(DocumentVersion, version_id)

    if not version:
        raise ValueError("DocumentVersion not found")

    return version.content


def update_processing_results(
    db: Session,
    version_id: UUID,
    extracted_text: str,
    classification,
    confidence: float,
    tags: list[str] | None = None,
):
    version = db.get(DocumentVersion, version_id)

    if not version:
        raise ValueError("DocumentVersion not found")

    version.extracted_text = extracted_text
    version.classification = classification
    version.confidence = confidence
    version.tags = tags or []
    version.processing_status = ProcessingStatus.uploaded

    db.commit()


def get_document_by_hash(
    db: Session,
    content_hash: str,
) -> Document | None:
    return (
        db.query(Document)
        .filter(Document.content_hash == content_hash)
        .one_or_none()
    )


def get_document_by_id(
    db: Session,
    document_id: UUID,
) -> Document | None:
    return db.get(Document, document_id)


def list_documents(db: Session):
    rows = (
        db.query(
            Document,
            DocumentVersion.processing_status,
            DocumentVersion.classification,
            DocumentVersion.confidence,
        )
        .outerjoin(
            DocumentVersion,
            Document.current_version_id == DocumentVersion.id,
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
            len(version_ids_by_document.get(doc.id, [])),
            (
                version_ids_by_document.get(doc.id, []).index(doc.current_version_id) + 1
                if doc.current_version_id and doc.current_version_id in version_ids_by_document.get(doc.id, [])
                else None
            ),
        )
        for doc, processing_status, classification, confidence in rows
    ]


def update_document_type(
    db: Session,
    document_id: UUID,
    document_type: str,
) -> Document | None:
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
    document = db.get(Document, document_id)

    if not document or not document.current_version_id:
        return None

    return db.get(DocumentVersion, document.current_version_id)


def get_document_version_by_id(
    db: Session,
    version_id: UUID,
) -> DocumentVersion | None:
    return db.get(DocumentVersion, version_id)


def list_existing_tags(
    db: Session,
) -> list[str]:
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
    document.current_version_id = version.id
    db.commit()
    db.refresh(document)


def delete_document(
    db: Session,
    document_id: UUID,
) -> None:
    """
    Deletes a document and all its versions.
    Raises ValueError if document does not exist.
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
