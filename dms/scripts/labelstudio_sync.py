import os
import sys
from pathlib import Path

# Ensure project root is on PYTHONPATH
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models.document_versions import DocumentVersion
from app.services.labelstudio.client import LabelStudioClient, LabelStudioConfig


def main() -> None:
    base_url = os.getenv("LABEL_STUDIO_URL", "").strip()
    api_token = os.getenv("LABEL_STUDIO_API_TOKEN", "").strip()
    project_id = int(os.getenv("LABEL_STUDIO_PROJECT_ID", "0"))
    if not base_url or not api_token or project_id <= 0:
        raise RuntimeError(
            "Set LABEL_STUDIO_URL, LABEL_STUDIO_API_TOKEN, LABEL_STUDIO_PROJECT_ID before running."
        )

    client = LabelStudioClient(
        LabelStudioConfig(
            base_url=base_url.rstrip("/"),
            api_token=api_token,
            project_id=project_id,
        )
    )

    db: Session = SessionLocal()
    try:
        rows = (
            db.query(DocumentVersion)
            .filter(DocumentVersion.extracted_text.isnot(None))
            .order_by(DocumentVersion.created_at.desc())
            .limit(25)
            .all()
        )
        for version in rows:
            filename = version.document.filename if version.document else str(version.id)
            text = version.extracted_text or ""
            client.create_task_for_document(
                doc_id=str(version.document_id),
                filename=filename,
                text=text,
            )
        print(f"Imported {len(rows)} task(s) into Label Studio project {project_id}.")
    finally:
        db.close()


if __name__ == "__main__":
    main()

