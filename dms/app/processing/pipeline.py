from sqlalchemy.orm import Session

from app.db.models.processing_jobs import ProcessingJob
from app.db.models.enums import ProcessingStatus
from app.workers.processor import process_job


def advance_pipeline(db: Session, job_id) -> None:
    job = (
        db.query(ProcessingJob)
        .filter(ProcessingJob.id == job_id)
        .one_or_none()
    )

    if not job:
        return

    if job.status != ProcessingStatus.pending:
        return

    process_job(db, job)
