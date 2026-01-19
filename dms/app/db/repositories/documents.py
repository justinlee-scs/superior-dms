from sqlalchemy.orm import Session
import uuid

from app.db.models import Document, DocumentVersion
from app.db.models.enums import DocumentClass



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
        processing_status="uploaded",  # REQUIRED (NOT NULL)
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