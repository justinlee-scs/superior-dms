from sqlalchemy.orm import Session

from app.db.models.document_versions import DocumentVersion
from app.db.models.enums import ProcessingStatus

from app.services.extraction.handwriting import is_handwritten
from app.services.extraction.icr import run_icr_model
from app.services.extraction.classify import classify_document


def process_document(
    db: Session,
    version_id: str,
    file_bytes: bytes,
) -> None:
    version = (
        db.query(DocumentVersion)
        .filter(DocumentVersion.id == version_id)
        .one_or_none()
    )

    if not version:
        return

    try:
        # TODO: convert PDF → images
        images = [file_bytes]  # placeholder

        if is_handwritten(file_bytes):
            text, confidence = run_icr_model(images)
        else:
            # TODO: replace with Tesseract OCR
            text = ""
            confidence = 0.0

        classification = classify_document(text)

        version.extracted_text = text
        version.classification = classification
        version.confidence = confidence
        version.processing_status = ProcessingStatus.uploaded

    except Exception:
        version.processing_status = ProcessingStatus.failed
        raise

    finally:
        db.commit()
