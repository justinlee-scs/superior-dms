from sqlalchemy.orm import Session

from app.db.models.document_versions import DocumentVersion
from app.db.models.enums import ProcessingStatus
from app.db.repositories.documents import list_existing_tags

from app.services.extraction.handwriting import is_handwritten
from app.services.extraction.icr import run_icr_model
from app.services.extraction.classify import classify_document
from app.services.extraction.tags import derive_tags

from app.services.extraction.ocr_sync import extract_text_from_file

def process_document(
    db: Session,
    version_id: str,
    file_bytes: bytes,
    *,
    commit: bool = True,
) -> None:
    version = (
        db.query(DocumentVersion)
        .filter(DocumentVersion.id == version_id)
        .one_or_none()
    )

    if not version:
        return

    try:
        text, confidence = extract_text_from_file(
        file_bytes=file_bytes,
        filename=version.document.filename,
)

        classification = classify_document(text)
        existing_tags = list_existing_tags(db)
        tags = derive_tags(
            text,
            classification,
            document_type=version.document.document_type,
            filename=version.document.filename,
            existing_tags=existing_tags,
        )

        version.extracted_text = text
        version.classification = classification
        version.confidence = confidence
        version.tags = tags
        version.processing_status = ProcessingStatus.uploaded

    except Exception:
        version.processing_status = ProcessingStatus.failed
        if commit:
            db.commit()
        else:
            db.flush()
        raise

    if commit:
        db.commit()
    else:
        db.flush()
