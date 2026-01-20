from sqlalchemy.orm import Session
from sqlalchemy import desc
import uuid
from uuid import UUID

from app.db.models import Document, DocumentVersion


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
    document_id,
) -> DocumentVersion:
    version = DocumentVersion(
        id=uuid.uuid4(),
        document_id=document_id,
        processing_status="uploaded",
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


def update_processing_results(
    db: Session,
    version_id,
    extracted_text: str,
    classification,
    confidence: float,
):
    version = db.get(DocumentVersion, version_id)

    version.extracted_text = extracted_text
    version.classification = classification
    version.confidence = confidence
    version.processing_status = "complete"

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
    document_id,
) -> Document | None:
    return db.get(Document, document_id)


def list_documents(db: Session):
    subq = (
        db.query(
            DocumentVersion.document_id,
            DocumentVersion.processing_status,
            DocumentVersion.classification,
            DocumentVersion.confidence,
        )
        .order_by(
            DocumentVersion.document_id,
            desc(DocumentVersion.created_at),
        )
        .distinct(DocumentVersion.document_id)
        .subquery()
    )

    return (
        db.query(
            Document,
            subq.c.processing_status,
            subq.c.classification,
            subq.c.confidence,
        )
        .outerjoin(subq, Document.id == subq.c.document_id)
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