from __future__ import annotations

import io
import logging
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
import requests

from app.db.repositories.documents import list_existing_tags
from app.db.repositories.tags import list_tag_pool
from app.db.session import get_db
from app.services.extraction.classify import classify_document_with_score, clear_classifier_cache
from app.services.extraction.handwriting import is_handwritten
from app.services.extraction.handwriting_model import clear_handwriting_cache
from app.services.extraction.field_extractor import clear_field_extractor_cache, predict_field_tokens
from app.services.extraction.tags import derive_tags, predict_model_tag_scores, clear_tagger_cache
from app.services.extraction.lilt import clear_lilt_cache

router = APIRouter(prefix="/labelstudio", tags=["labelstudio"])
logger = logging.getLogger(__name__)

_train_lock = threading.Lock()
_train_timer: threading.Timer | None = None
_train_in_progress = False
_train_pending = False
_last_train_requested_at = 0.0
_last_train_started_at = 0.0
_last_train_finished_at = 0.0
_last_train_status = "never"
_last_train_return_code: int | None = None
_next_train_scheduled_at: float | None = None


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

    classification, class_score = classify_document_with_score(text)
    tag_scores = predict_model_tag_scores(text)
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

    if _env("LS_ENABLE_FIELD_PREDICTIONS", "true").lower() in {"1", "true", "yes"}:
        rect_from = _env("LS_FROM_RECTANGLES", "rectangles")
        rect_to = _env("LS_TO_IMAGE", "pdf")
        image_url = data.get("image") or data.get("image_url")
        if isinstance(image_url, str) and image_url:
            try:
                img_bytes = None
                filename_hint = Path(image_url).name
                if image_url.startswith("http"):
                    resp = requests.get(image_url, timeout=15)
                    resp.raise_for_status()
                    img_bytes = resp.content
                elif image_url.startswith("/data/local-files/"):
                    root = os.getenv("LOCAL_FILES_DOCUMENT_ROOT", _root_dir())
                    rel = image_url[len("/data/local-files/") :].lstrip("/")
                    path = Path(root) / rel
                    if path.exists():
                        img_bytes = path.read_bytes()
                        filename_hint = path.name
                if img_bytes:
                    tokens = predict_field_tokens(img_bytes, filename_hint)
                    for token in tokens:
                        results.append(
                            {
                                "from_name": rect_from,
                                "to_name": rect_to,
                                "type": "rectanglelabels",
                                "value": {
                                    "x": float(token["x"]) * 100.0,
                                    "y": float(token["y"]) * 100.0,
                                    "width": float(token["w"]) * 100.0,
                                    "height": float(token["h"]) * 100.0,
                                    "rotation": 0,
                                    "rectanglelabels": [str(token["label"])],
                                },
                                "score": float(token["confidence"]),
                            }
                        )
            except Exception as exc:
                logger.warning("Field prediction failed: %s", exc)

    tag_conf = 0.0
    if tag_scores and tags:
        tag_conf = max(tag_scores.get(tag, 0.0) for tag in tags)
    overall_score = max(class_score, tag_conf)

    return {
        "result": results,
        "score": float(overall_score),
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


def _root_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def _training_command() -> list[str]:
    script = _root_dir() / "scripts" / "training" / "run_training_pipeline.sh"
    return ["bash", str(script)]


def _apply_default_model_paths() -> None:
    root = _root_dir()
    model_dir = root / "output" / "models"
    os.environ.setdefault("DOC_CLASS_MODEL_PATH", str(model_dir / "doc_classifier.joblib"))
    os.environ.setdefault("TAGGER_MODEL_PATH", str(model_dir / "tagger.joblib"))
    os.environ.setdefault("HANDWRITING_MODEL_PATH", str(model_dir / "handwriting.pt"))
    os.environ.setdefault("TROCR_MODEL_PATH", str(model_dir / "trocr"))
    os.environ.setdefault("FIELD_EXTRACTOR_MODEL_PATH", str(model_dir / "field_extractor.joblib"))


def _run_training_job() -> None:
    global _train_in_progress, _train_pending, _last_train_started_at, _last_train_finished_at
    global _last_train_status, _last_train_return_code, _next_train_scheduled_at
    with _train_lock:
        if _train_in_progress:
            _train_pending = True
            return
        _train_in_progress = True
        _train_pending = False
        _last_train_started_at = time.time()
        _next_train_scheduled_at = None

    try:
        _apply_default_model_paths()
        env = os.environ.copy()
        if _env("LABELSTUDIO_TRAIN_SKIP_TROCR", "").lower() in {"1", "true", "yes"}:
            env["SKIP_TROCR"] = "true"
        logger.info("Label Studio training: starting pipeline.")
        result = subprocess.run(
            _training_command(),
            cwd=_root_dir(),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        _last_train_return_code = result.returncode
        if result.returncode != 0:
            _last_train_status = "failed"
            logger.warning(
                "Label Studio training failed (code %s). Output:\n%s",
                result.returncode,
                result.stdout,
            )
        else:
            _last_train_status = "success"
            logger.info("Label Studio training completed successfully.")
            clear_classifier_cache()
            clear_tagger_cache()
            clear_handwriting_cache()
            clear_field_extractor_cache()
            clear_lilt_cache()
    except Exception as exc:
        _last_train_status = "crashed"
        _last_train_return_code = None
        logger.exception("Label Studio training crashed: %s", exc)
    finally:
        with _train_lock:
            _train_in_progress = False
            _last_train_finished_at = time.time()
            if _train_pending:
                _train_pending = False
                _schedule_training()


def _debounce_seconds() -> int:
    try:
        return max(10, int(_env("LABELSTUDIO_TRAIN_DEBOUNCE_SECONDS", "600")))
    except ValueError:
        return 600


def _cooldown_seconds() -> int:
    try:
        return max(0, int(_env("LABELSTUDIO_TRAIN_COOLDOWN_SECONDS", "300")))
    except ValueError:
        return 300


def _schedule_training() -> None:
    global _train_timer, _last_train_requested_at, _next_train_scheduled_at
    delay = _debounce_seconds()
    _last_train_requested_at = time.time()

    if _train_timer is not None:
        _train_timer.cancel()

    cooldown = _cooldown_seconds()
    eligible_at = _last_train_finished_at + cooldown if _last_train_finished_at else 0.0
    scheduled_at = max(_last_train_requested_at + delay, eligible_at)
    _next_train_scheduled_at = scheduled_at

    def _fire() -> None:
        _run_training_job()

    _train_timer = threading.Timer(max(0.0, scheduled_at - time.time()), _fire)
    _train_timer.daemon = True
    _train_timer.start()


def _snapshot_state() -> dict[str, Any]:
    with _train_lock:
        return {
            "in_progress": _train_in_progress,
            "pending": _train_pending,
            "last_requested_at": _last_train_requested_at or None,
            "last_started_at": _last_train_started_at or None,
            "last_finished_at": _last_train_finished_at or None,
            "last_status": _last_train_status,
            "last_return_code": _last_train_return_code,
            "next_scheduled_at": _next_train_scheduled_at,
            "debounce_seconds": _debounce_seconds(),
            "cooldown_seconds": _cooldown_seconds(),
        }


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/setup")
def setup(payload: dict[str, Any]) -> dict[str, Any]:
    return {"status": "ok", "payload_keys": sorted(payload.keys())}


@router.post("/predict")
async def predict(request: Request, db: Session = Depends(get_db)) -> Any:
    try:
        payload: Any = await request.json()
    except Exception:
        payload = []
    tasks, wrapped = _parse_tasks(payload)
    existing_tags = _build_existing_tag_pool(db)
    predictions = [_predict_for_task(task.get("data", {}), existing_tags=existing_tags) for task in tasks]
    if wrapped:
        return {"results": predictions}
    return predictions


@router.post("/train")
def train(payload: dict[str, Any]) -> dict[str, Any]:
    enabled = _env("LABELSTUDIO_TRAIN_ENABLED", "true").lower() in {"1", "true", "yes"}
    if not enabled:
        return {"status": "disabled", "detail": "training disabled by LABELSTUDIO_TRAIN_ENABLED"}
    _schedule_training()
    state = _snapshot_state()
    return {"status": "queued", "detail": "training scheduled (debounced)", "state": state}


@router.get("/train/status")
def train_status() -> dict[str, Any]:
    return _snapshot_state()


@router.post("/webhook")
def webhook(payload: dict[str, Any]) -> dict[str, Any]:
    """Label Studio webhook entrypoint. Schedules debounced training."""
    enabled = _env("LABELSTUDIO_TRAIN_ENABLED", "true").lower() in {"1", "true", "yes"}
    if not enabled:
        return {"status": "disabled", "detail": "training disabled by LABELSTUDIO_TRAIN_ENABLED"}
    _schedule_training()
    return {"status": "queued", "detail": "training scheduled (debounced)", "state": _snapshot_state()}
