from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.repositories.documents import list_existing_tags
from app.db.repositories.tags import list_tag_pool
from app.db.session import get_db
from app.services.extraction.classify import classify_document
from app.services.extraction.handwriting import is_handwritten
from app.services.extraction.tags import derive_tags

router = APIRouter(prefix="/labelstudio", tags=["labelstudio"])


def _env(key: str, default: str) -> str:
    return os.getenv(key, default).strip()


def _choice_result(*, from_name: str, to_name: str, choices: list[str]) -> dict[str, Any]:
    return {
        "from_name": from_name,
        "to_name": to_name,
        "type": "choices",
        "value": {"choices": choices},
    }


def _build_existing_tag_pool(db: Session) -> list[str]:
    pool = set(list_tag_pool(db=db))
    pool.update(list_existing_tags(db=db))
    return sorted(pool)


def _extract_text(data: dict[str, Any]) -> str:
    for key in ("ocr_text", "text", "content", "document_text"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _predict_for_task(
    data: dict[str, Any],
    *,
    existing_tags: list[str],
) -> dict[str, Any]:
    text = _extract_text(data)
    filename = data.get("filename")

    classification = classify_document(text)
    tags = derive_tags(
        text,
        classification,
        filename=filename,
        existing_tags=existing_tags,
    )

    results: list[dict[str, Any]] = []

    doc_type_from = _env("LS_FROM_DOCUMENT_TYPE", "document_type")
    tags_from = _env("LS_FROM_TAGS", "tags")
    handwriting_from = _env("LS_FROM_HANDWRITING", "handwriting")
    to_name = _env("LS_TO_NAME", "ocr_text")

    if classification:
        results.append(
            _choice_result(
                from_name=doc_type_from,
                to_name=to_name,
                choices=[str(classification.value)],
            )
        )

    if tags:
        results.append(
            _choice_result(
                from_name=tags_from,
                to_name=to_name,
                choices=tags,
            )
        )

    # Handwriting detection is image-based; default to "unknown" if no images are provided.
    handwriting_choice = None
    if "images" in data and isinstance(data["images"], list):
        # Placeholder: without real image bytes, we cannot detect handwriting.
        handwriting_choice = "unknown"
    elif "image" in data or "image_url" in data:
        handwriting_choice = "unknown"

    if handwriting_choice:
        results.append(
            _choice_result(
                from_name=handwriting_from,
                to_name=to_name,
                choices=[handwriting_choice],
            )
        )

    return {
        "result": results,
        "score": 0.5,
        "model_version": _env("LS_MODEL_VERSION", "dms-ml-0.1"),
    }


def _parse_tasks(payload: Any) -> tuple[list[dict[str, Any]], bool]:
    if isinstance(payload, list):
        return payload, False
    if isinstance(payload, dict):
        if "tasks" in payload and isinstance(payload["tasks"], list):
            return payload["tasks"], True
        if "data" in payload and isinstance(payload["data"], dict):
            return [payload], False
    return [], False


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/setup")
def setup(payload: dict[str, Any]) -> dict[str, Any]:
    return {"status": "ok", "payload_keys": sorted(payload.keys())}


@router.post("/predict")
def predict(payload: Any, db: Session = Depends(get_db)) -> Any:
    tasks, wrapped = _parse_tasks(payload)
    existing_tags = _build_existing_tag_pool(db)
    predictions = [_predict_for_task(task.get("data", {}), existing_tags=existing_tags) for task in tasks]
    if wrapped:
        return {"results": predictions}
    return predictions


@router.post("/train")
def train(payload: dict[str, Any]) -> dict[str, Any]:
    return {"status": "ok", "detail": "training not implemented yet"}
