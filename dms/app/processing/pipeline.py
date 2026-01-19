from sqlalchemy.orm import Session

from app.db.repositories.documents import update_processing_results
from app.db.models.enums import DocumentClass

from app.services.extraction.ocr import run_tesseract
from app.services.extraction.icr import run_icr_model
from app.services.extraction.classify import classify_document
from app.services.extraction.pdf import pdf_to_images


def process_document(
    db: Session,
    version_id: str,
    file_bytes: bytes,
):
    # Convert PDF to images
    images = pdf_to_images(file_bytes)

    # 1. ALWAYS attempt OCR first
    ocr_text, ocr_confidence = run_tesseract(images)

    # 2. Decide if OCR is usable
    if not ocr_text or ocr_confidence < 0.6:
        # Fallback to ICR only if OCR is poor
        text, confidence = run_icr_model(images)
    else:
        text, confidence = ocr_text, ocr_confidence

    # 3. Classify extracted text
    classification = classify_document(text)

    # 4. Persist results
    update_processing_results(
        db=db,
        version_id=version_id,
        extracted_text=text,
        classification=classification or DocumentClass.UNKNOWN,
        confidence=confidence,
    )
