from sqlalchemy.orm import Session

from app.db.models.processing_jobs import ProcessingJob
from app.db.models.enums import (
    ProcessingStage,
    ProcessingStatus,
    DocumentClass,
)

from app.db.repositories.documents import update_processing_results

from app.services.extraction.pdf import pdf_to_images
from app.services.extraction.ocr import run_tesseract
from app.services.extraction.icr import run_icr_model
from app.services.extraction.classify import classify_document


def process_job(db: Session, job: ProcessingJob) -> None:
    """
    Execute exactly one processing stage for a job.
    Safe to retry. Safe to resume.
    """

    try:
        # Mark running
        job.status = ProcessingStatus.RUNNING
        db.commit()

        version_id = job.document_version_id

        # =========================
        # STAGE 1: CLASSIFICATION (FORMAT-LEVEL)
        # =========================
        if job.stage == ProcessingStage.CLASSIFICATION:
            # NOTE:
            # At this stage we are NOT doing semantic classification.
            # We are only preparing for OCR (e.g., PDF → images).
            # No persistence of results yet.

            # Transition only
            job.stage = ProcessingStage.OCR
            job.status = ProcessingStatus.[pending]
            db.commit()
            return

        # =========================
        # STAGE 2: OCR / ICR
        # =========================
        if job.stage == ProcessingStage.OCR:
            # Load binary via repository / storage layer
            # (Assumed to be handled inside pdf_to_images or lower layers)
            images = pdf_to_images(version_id)

            ocr_text, ocr_confidence = run_tesseract(images)

            if not ocr_text or ocr_confidence < 0.6:
                text, confidence = run_icr_model(images)
            else:
                text, confidence = ocr_text, ocr_confidence

            job.result = {
                "text": text,
                "confidence": confidence,
            }

            job.stage = ProcessingStage.POST_PROCESS
            job.status = ProcessingStatus.pending
            db.commit()
            return

        # =========================
        # STAGE 3: POST_PROCESS (SEMANTIC)
        # =========================
        if job.stage == ProcessingStage.POST_PROCESS:
            text = (job.result or {}).get("text")
            confidence = (job.result or {}).get("confidence")

            classification = classify_document(text) or DocumentClass.UNKNOWN

            update_processing_results(
                db=db,
                version_id=version_id,
                extracted_text=text,
                classification=classification,
                confidence=confidence,
            )

            job.status = ProcessingStatus.COMPLETE
            db.commit()
            return

    except Exception as exc:
        db.rollback()
        job.status = ProcessingStatus.failed
        job.result = {
            "error": str(exc),
        }
        db.commit()
