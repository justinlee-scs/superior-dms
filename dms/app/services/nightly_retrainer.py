from __future__ import annotations

import logging
import os
import subprocess
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy.exc import SQLAlchemyError

from app.db.models.retrain_schedule_setting import RetrainScheduleSetting
from app.db.session import SessionLocal
from app.services.extraction.classify import clear_classifier_cache
from app.services.extraction.field_extractor import clear_field_extractor_cache
from app.services.extraction.handwriting_model import clear_handwriting_cache
from app.services.extraction.tags import clear_tagger_cache
from app.services.extraction.lilt import clear_lilt_cache

logger = logging.getLogger(__name__)

_thread: threading.Thread | None = None
_run_lock = threading.Lock()
_reload_event = threading.Event()


def _env_enabled() -> bool:
    return os.getenv("NIGHTLY_RETRAIN_ENABLED", "true").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def _env_timezone_name() -> str:
    return os.getenv("NIGHTLY_RETRAIN_TZ", "America/Los_Angeles").strip() or "America/Los_Angeles"


def _env_hour() -> int:
    try:
        value = int(os.getenv("NIGHTLY_RETRAIN_HOUR", "3"))
    except ValueError:
        value = 3
    return min(max(value, 0), 23)


def _env_minute() -> int:
    try:
        value = int(os.getenv("NIGHTLY_RETRAIN_MINUTE", "0"))
    except ValueError:
        value = 0
    return min(max(value, 0), 59)


def _root_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def _next_run_time(now: datetime, tz: ZoneInfo, hour: int, minute: int) -> datetime:
    target = now.astimezone(tz).replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0,
    )
    if target <= now.astimezone(tz):
        target = target + timedelta(days=1)
    return target


def _run_training_pipeline() -> None:
    script = _root_dir() / "scripts" / "training" / "run_training_pipeline.sh"
    env = os.environ.copy()
    env.setdefault("SKIP_TROCR", "true")
    env.setdefault("SKIP_LILT", "false")

    logger.info("Nightly retrain: starting training pipeline.")
    result = subprocess.run(
        ["bash", str(script)],
        cwd=_root_dir(),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        logger.warning(
            "Nightly retrain failed (code %s). Output:\n%s",
            result.returncode,
            result.stdout,
        )
        return

    logger.info("Nightly retrain completed successfully.")
    clear_classifier_cache()
    clear_tagger_cache()
    clear_handwriting_cache()
    clear_field_extractor_cache()
    clear_lilt_cache()


def _get_schedule() -> tuple[bool, str, int, int]:
    enabled = _env_enabled()
    timezone_name = _env_timezone_name()
    hour = _env_hour()
    minute = _env_minute()

    db = SessionLocal()
    try:
        row = db.get(RetrainScheduleSetting, 1)
        if row:
            enabled = bool(row.enabled)
            timezone_name = (row.timezone or timezone_name).strip() or timezone_name
            hour = min(max(int(row.hour), 0), 23)
            minute = min(max(int(row.minute), 0), 59)
    except (SQLAlchemyError, ValueError, TypeError):
        pass
    finally:
        db.close()

    return enabled, timezone_name, hour, minute


def _loop() -> None:
    while True:
        enabled, timezone_name, hour, minute = _get_schedule()
        try:
            tz = ZoneInfo(timezone_name)
        except Exception:
            tz = ZoneInfo("America/Los_Angeles")
            timezone_name = tz.key

        if not enabled:
            logger.info("Nightly retrain disabled; waiting for schedule updates.")
            _reload_event.wait(timeout=60)
            _reload_event.clear()
            continue

        now = datetime.now(tz)
        next_run = _next_run_time(now, tz, hour, minute)
        wait_seconds = max(1, int((next_run - now).total_seconds()))
        logger.info(
            "Nightly retrain scheduler armed for %s (%s) at %02d:%02d.",
            next_run.isoformat(),
            tz.key,
            hour,
            minute,
        )

        # Allow schedule changes to take effect without restart.
        reloaded = _reload_event.wait(timeout=wait_seconds)
        _reload_event.clear()
        if reloaded:
            continue

        if not _run_lock.acquire(blocking=False):
            logger.info("Nightly retrain skipped: previous run still in progress.")
            continue
        try:
            _run_training_pipeline()
        finally:
            _run_lock.release()


def start_nightly_retrainer() -> None:
    global _thread
    if _thread and _thread.is_alive():
        return
    _thread = threading.Thread(target=_loop, name="nightly-retrainer", daemon=True)
    _thread.start()


def reload_nightly_retrainer() -> None:
    _reload_event.set()
