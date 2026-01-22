from sqlalchemy.orm import Session
from sqlalchemy import desc
import uuid
from uuid import UUID

from app.db.models import Document, DocumentVersion
from app.db.models.enums import ProcessingStatus


def create_document(
    db: Session,
    filename: str,
    content_hash: str,
) -> Document:
    document = Document(
        id=uuid.uuid4(),
        filename=filename,
        content_hash=content_hash,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def create_document_version(
    db: Session,
    document_id: UUID,
    file_bytes: bytes,
) -> DocumentVersion:
    version = DocumentVersion(
        id=uuid.uuid4(),
        document_id=document_id,
        content=file_bytes,
        processing_status=ProcessingStatus.uploaded,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
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
):
    version = db.get(DocumentVersion, version_id)

    if not version:
        raise ValueError("DocumentVersion not found")

    version.extracted_text = extracted_text
    version.classification = classification
    version.confidence = confidence
    version.processing_status = ProcessingStatus.COMPLETED

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
    return (
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
