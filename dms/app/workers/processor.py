import threading
from uuid import UUID

from sqlalchemy.orm import Session

from app.processing.pipeline import process_document
from app.db.repositories.documents import load_document_version_bytes
from app.db.models.document_versions import DocumentVersion
from app.db.models.enums import ProcessingStatus
from app.db.session import SessionLocal


def process_document_version(db: Session, version_id: str | UUID) -> None:
    """Synchronous processor for a DocumentVersion."""

    try:
        normalized_version_id = UUID(str(version_id))
    except (TypeError, ValueError):
        normalized_version_id = version_id

    version = db.get(DocumentVersion, normalized_version_id)
    if not version:
        return

    try:
        version.processing_status = ProcessingStatus.processing

        file_bytes = load_document_version_bytes(db, normalized_version_id)

        process_document(
            db=db,
            version_id=normalized_version_id,
            file_bytes=file_bytes,
            commit=True,
        )

    except Exception:
        version = db.get(DocumentVersion, normalized_version_id)
        if version:
            version.processing_status = ProcessingStatus.failed
            db.commit()
        raise


def _process_in_background(version_id: str | UUID) -> None:
    db = SessionLocal()
    try:
        process_document_version(db, version_id)
    finally:
        db.close()


def enqueue_processing(version_id: str | UUID) -> None:
    """Queue processing using an in-process background thread."""
    thread = threading.Thread(
        target=_process_in_background,
        args=(version_id,),
        daemon=True,
    )
    thread.start()


# import time
# import threading
# from uuid import UUID

# from sqlalchemy.orm import Session

# from app.db.repositories.documents import (
#     list_existing_tags,
#     load_document_version_bytes,
#     update_processing_results,
# )
# from app.services.extraction.pdf import pdf_to_images
# from app.services.extraction.ocr import run_tesseract
# from app.services.extraction.icr import run_icr_model
# from app.services.extraction.classify import classify_document
# from app.services.extraction.tags import derive_tags
# from app.services.extraction.field_extractor import extract_fields, fields_to_tags
# from app.db.models.enums import DocumentClass, ProcessingStatus
# from app.db.models.document_versions import DocumentVersion
# from app.db.session import SessionLocal


# def process_document_version(db: Session, version_id: str | UUID) -> None:
#     """Synchronous processor for a DocumentVersion.

#     Parameters:
#         db (type=Session): Database session used for persistence operations.
#         version_id (type=str): Identifier used to locate the target record.
#     """

#     try:
#         normalized_version_id = UUID(str(version_id))
#     except (TypeError, ValueError):
#         normalized_version_id = version_id

#     try:
#         start = time.perf_counter()
#         version = db.get(DocumentVersion, normalized_version_id)
#         if not version:
#             return
#         version.processing_status = ProcessingStatus.processing

#         # Load raw bytes from repository
#         file_bytes = load_document_version_bytes(db, normalized_version_id)

#         # Convert PDF/images to PIL images
#         images = pdf_to_images(file_bytes)

#         # 1. Attempt OCR first
#         ocr_text, ocr_confidence = run_tesseract(images)

#         # 2. Fallback to ICR if OCR confidence is low
#         if not ocr_text or ocr_confidence < 0.6:
#             text, confidence = run_icr_model(images)
#             ocr_engine = "tesseract+icr_fallback"
#             ocr_model_version = "pytesseract+placeholder_icr"
#         else:
#             text, confidence = ocr_text, ocr_confidence
#             ocr_engine = "tesseract"
#             ocr_model_version = "pytesseract"
#         ocr_latency_ms = int((time.perf_counter() - start) * 1000)

#         # 3. Classify extracted text
#         classification = classify_document(text) or DocumentClass.UNKNOWN
#         existing_tags = list_existing_tags(db)
#         tags = derive_tags(
#             text,
#             classification,
#             document_type=version.document.document_type,
#             filename=version.document.filename,
#             existing_tags=existing_tags,
#         )
#         field_values = extract_fields(file_bytes, version.document.filename)
#         if field_values:
#             tags.extend(fields_to_tags(field_values))

#         # 4. Persist results
#         update_processing_results(
#             db=db,
#             version_id=normalized_version_id,
#             extracted_text=text,
#             classification=classification,
#             confidence=confidence,
#             tags=tags,
#             ocr_raw_confidence=ocr_confidence,
#             ocr_engine=ocr_engine,
#             ocr_model_version=ocr_model_version,
#             ocr_latency_ms=ocr_latency_ms,
#         )

#     except Exception:
#         # If any error occurs, mark version as failed
#         version = db.get(DocumentVersion, normalized_version_id)
#         if version:
#             version.processing_status = ProcessingStatus.failed
#             db.commit()
#         raise


# def _process_in_background(version_id: str | UUID) -> None:
#     db = SessionLocal()
#     try:
#         process_document_version(db, version_id)
#     finally:
#         db.close()


# def enqueue_processing(version_id: str | UUID) -> None:
#     """Queue processing using an in-process background thread."""
#     thread = threading.Thread(
#         target=_process_in_background,
#         args=(version_id,),
#         daemon=True,
#     )
#     thread.start()
