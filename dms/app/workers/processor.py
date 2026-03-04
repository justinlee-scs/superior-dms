from sqlalchemy.orm import Session

from app.db.repositories.documents import (
    list_existing_tags,
    load_document_version_bytes,
    update_processing_results,
)
from app.services.extraction.pdf import pdf_to_images
from app.services.extraction.ocr import run_tesseract
from app.services.extraction.icr import run_icr_model
from app.services.extraction.classify import classify_document
from app.services.extraction.tags import derive_tags
from app.db.models.enums import DocumentClass, ProcessingStatus
from app.db.models.document_versions import DocumentVersion


def process_document_version(db: Session, version_id: str) -> None:
    """
    Synchronous processor for a DocumentVersion.
    Runs OCR/ICR, classifies, and updates the version.
    """

    try:
        version = db.get(DocumentVersion, version_id)
        if not version:
            return

        # Load raw bytes from repository
        file_bytes = load_document_version_bytes(db, version_id)

        # Convert PDF/images to PIL images
        images = pdf_to_images(file_bytes)

        # 1. Attempt OCR first
        ocr_text, ocr_confidence = run_tesseract(images)

        # 2. Fallback to ICR if OCR confidence is low
        if not ocr_text or ocr_confidence < 0.6:
            text, confidence = run_icr_model(images)
        else:
            text, confidence = ocr_text, ocr_confidence

        # 3. Classify extracted text
        classification = classify_document(text) or DocumentClass.UNKNOWN
        existing_tags = list_existing_tags(db)
        tags = derive_tags(
            text,
            classification,
            document_type=version.document.document_type,
            filename=version.document.filename,
            existing_tags=existing_tags,
        )

        # 4. Persist results
        update_processing_results(
            db=db,
            version_id=version_id,
            extracted_text=text,
            classification=classification,
            confidence=confidence,
            tags=tags,
        )

    except Exception as exc:
        # If any error occurs, mark version as failed
        version = db.get(DocumentVersion, version_id)
        if version:
            version.processing_status = ProcessingStatus.failed
            db.commit()
        raise
