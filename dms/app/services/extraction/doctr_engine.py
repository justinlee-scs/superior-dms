"""
doctr_engine.py

Replacement for app/services/extraction/lilt.py. The public entrypoint is
run_doctr_extraction(*, file_bytes, filename) -> ExtractionResult - named
for what it actually does, not for the model it replaces. pipeline.py's
import and call site need updating to match (that edit lives in the
pipeline.py step, not here): change
    from app.services.extraction.lilt import run_lilt_model
to
    from app.services.extraction.doctr_engine import run_doctr_extraction
and update the call site variable name away from `lilt_result` for the
same reason - a misleading name left in place just because renaming
touches one more line isn't worth the confusion.

ExtractionResult keeps the same (text, confidence, fields) fields as the
old LiLTResult in the same position, so any code that only reads those
three attributes still works unmodified even though the type/function
names changed.

NOTE: per-word confidence data (ocr_low_confidence, ocr_confidence_lowest,
ocr_confidence_average, word_boxes, processing_log) is NEW - lilt.py never
exposed this. pipeline.py needs an explicit, separate edit to read these
additive attributes and persist them to the columns added by the
correction-queue migration.

Pipeline: DocTR (detection + recognition, per-word confidence) -> Ollama
(field-level KIE over the OCR'd text) -> ExtractionResult.

Weights:
    detection:   db_resnet50      (quality-first per project requirement;
                                    db_mobilenet_v3_large traded off for
                                    speed we don't need on a batch pipeline)
    recognition: parseq           (attention-based; stronger on the
                                    alphanumeric strings that dominate our
                                    target fields - invoice #, account #,
                                    GST/PST numbers - than CTC-based crnn)

    Swap RECOGNITION_ARCH to "crnn_vgg16_bn" below if PARSeq fine-tuning
    support turns out to be too immature when you get to the retrain loop -
    flagged as an open risk in the pipeline design notes.

Confidence policy:
    - Per-word confidence comes straight from DocTR's recognition output.
    - ZERO TOLERANCE: a document is flagged if EVEN ONE word falls below
      CONFIDENCE_THRESHOLD. No ratio, no percentage tolerance - this is
      deliberate per the project's "perfect source-of-truth data" goal
      for the training loop. A single uncertain word is enough to route
      the whole document to the correction queue.
    - Every flagged document is not auto-accepted, full stop. Every
      low-confidence word must be corrected or explicitly confirmed
      before extraction_corrected_jsonb can be finalized (enforced in
      the correction queue API, not here).

Timing:
    - Every call records wall-clock start/end timestamps for each stage
      (doctr_ocr, ollama_kie) plus the total, via ExtractionTimer below.
    - Rendered to a human-readable text block (ExtractionResult.processing_log)
      for storage in document_versions - useful for evaluating how much
      time a training/tuning pass can afford to spend, per your request.
    - Verbose mode (OCR_VERBOSE_LOGGING=true) includes per-stage start/end
      ISO timestamps; non-verbose (default) is a compact one-line-per-stage
      duration summary.
"""

from __future__ import annotations

import io
import json
import logging
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

import requests
from doctr.io import DocumentFile
from doctr.models import ocr_predictor, db_resnet50, parseq

logger = logging.getLogger(__name__)

VERBOSE = os.environ.get("OCR_VERBOSE_LOGGING", "false").strip().lower() in {"1", "true", "yes"}


# --------------------------------------------------------------------------
# Timing / logging
# --------------------------------------------------------------------------

class ExtractionTimer:
    """Records wall-clock start/end timestamps for the overall extraction
    and each named stage inside it, then renders as human-readable text
    for storage (document_versions.ocr_processing_log).

    Usage:
        timer = ExtractionTimer(verbose=VERBOSE).start()
        with timer.stage("doctr_ocr"):
            ...
        with timer.stage("ollama_kie"):
            ...
        log_text = timer.finish()
    """

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self._start: Optional[datetime] = None
        self._end: Optional[datetime] = None
        self._stages: list[tuple[str, datetime, datetime]] = []

    def start(self) -> "ExtractionTimer":
        self._start = datetime.now(timezone.utc)
        return self

    @contextmanager
    def stage(self, name: str) -> Iterator[None]:
        t0 = datetime.now(timezone.utc)
        try:
            yield
        finally:
            t1 = datetime.now(timezone.utc)
            self._stages.append((name, t0, t1))
            if self.verbose:
                logger.info(
                    "Extraction stage=%s start=%s end=%s duration_ms=%.0f",
                    name, t0.isoformat(), t1.isoformat(),
                    (t1 - t0).total_seconds() * 1000,
                )

    def finish(self) -> str:
        self._end = datetime.now(timezone.utc)
        total_ms = (self._end - self._start).total_seconds() * 1000 if self._start else 0.0

        lines = [
            f"start={self._start.isoformat() if self._start else 'unknown'} "
            f"end={self._end.isoformat()} total_ms={total_ms:.0f}"
        ]
        for name, t0, t1 in self._stages:
            dur_ms = (t1 - t0).total_seconds() * 1000
            if self.verbose:
                lines.append(
                    f"  [{name}] start={t0.isoformat()} end={t1.isoformat()} duration_ms={dur_ms:.0f}"
                )
            else:
                lines.append(f"  [{name}] duration_ms={dur_ms:.0f}")
        return "\n".join(lines)


# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------

CONFIDENCE_THRESHOLD = float(os.environ.get("OCR_CONFIDENCE_THRESHOLD", "0.70"))
# Zero tolerance: ANY word below CONFIDENCE_THRESHOLD flags the document.
# No ratio/percentage tolerance - see confidence policy note above.

DETECTION_ARCH = os.environ.get("DOCTR_DETECTION_ARCH", "db_resnet50")
RECOGNITION_ARCH = os.environ.get("DOCTR_RECOGNITION_ARCH", "parseq")

WEIGHTS_ROOT = Path(os.environ.get("DOCTR_WEIGHTS_ROOT", "ai-training/models/doctr"))
DETECTION_WEIGHTS = WEIGHTS_ROOT / "detection" / "current" / "weights.pt"
RECOGNITION_WEIGHTS = WEIGHTS_ROOT / "recognition" / "current" / "weights.pt"

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1")
OLLAMA_MAX_CHARS = int(os.environ.get("OLLAMA_MAX_CHARS", "60000"))
OLLAMA_MAX_RETRIES = 2

TARGET_FIELDS = [
    "document_type", "vendor", "invoice_number", "document_date",
    "due_date", "grand_total", "bill_to", "account_number",
    "gst_number", "pst_number",
]

_KIE_PROMPT = """You are extracting structured fields from OCR'd business document text.
Return ONLY a JSON object with these exact keys (use null if a field is absent):
{fields}

Rules:
- "vendor" is the supplier/issuer of the document, never the recipient (SCS / Superior City Services / Superior City Contracting Services is almost always the recipient, not the vendor).
- Dates in YYYY-MM-DD format where determinable.
- grand_total as a plain number string, no currency symbol.
- No commentary, no markdown fences, JSON only.

OCR TEXT:
{text}
"""


# --------------------------------------------------------------------------
# ExtractionResult
#
# (text, confidence, fields) sit first and match the old LiLTResult shape
# exactly, so any code that only reads those three attributes still works.
# Everything after `fields` is NEW - DocTR gives us per-word confidence and
# per-stage timing that LiLT/LayoutLMv3 never did.
# --------------------------------------------------------------------------

@dataclass
class ExtractionResult:
    text: str
    confidence: Optional[float]
    fields: Dict[str, Any]

    ocr_confidence_average: float = 0.0
    ocr_confidence_lowest: float = 0.0
    ocr_low_confidence: bool = False
    word_boxes: List[Dict[str, Any]] = field(default_factory=list)
    extraction_raw_jsonb: Dict[str, Any] = field(default_factory=dict)
    engine: str = "doctr+ollama"
    engine_meta: Dict[str, Any] = field(default_factory=dict)
    processing_log: str = ""


# --------------------------------------------------------------------------
# Model loading (cached at module scope - loaded once per worker process)
# --------------------------------------------------------------------------

_predictor = None


def _load_predictor():
    global _predictor
    if _predictor is not None:
        return _predictor

    det_arch = DETECTION_ARCH
    reco_arch = RECOGNITION_ARCH

    predictor = ocr_predictor(
        det_arch=det_arch,
        reco_arch=reco_arch,
        pretrained=True,
        assume_straight_pages=True,
    )

    # Overlay fine-tuned weights if a retrain loop has produced a `current/`
    # checkpoint; otherwise fall back silently to the pretrained weights
    # doctr already downloaded.
    import torch

    if DETECTION_WEIGHTS.exists():
        predictor.det_predictor.model.load_state_dict(
            torch.load(DETECTION_WEIGHTS, map_location="cpu")
        )
    if RECOGNITION_WEIGHTS.exists():
        predictor.reco_predictor.model.load_state_dict(
            torch.load(RECOGNITION_WEIGHTS, map_location="cpu")
        )

    _predictor = predictor
    return _predictor


# --------------------------------------------------------------------------
# DocTR pass -> per-word confidence + plain text
# --------------------------------------------------------------------------

def _run_doctr(file_bytes: bytes, filename: str) -> dict[str, Any]:
    predictor = _load_predictor()

    suffix = Path(filename or "").suffix.lower()
    # doctr's DocumentFile accepts raw bytes directly - no temp file needed,
    # matching lilt.py's in-memory handling (it never touches disk either).
    if suffix == ".pdf":
        doc = DocumentFile.from_pdf(file_bytes)
    else:
        doc = DocumentFile.from_images(file_bytes)

    result = predictor(doc)

    words: list[dict[str, Any]] = []
    text_lines: list[str] = []

    for page_idx, page in enumerate(result.pages):
        for block in page.blocks:
            for line in block.lines:
                line_text = []
                for w in line.words:
                    (x0, y0), (x1, y1) = w.geometry
                    words.append({
                        "page": page_idx,
                        "text": w.value,
                        "confidence": round(float(w.confidence), 4),
                        "bbox": [round(x0, 4), round(y0, 4), round(x1, 4), round(y1, 4)],
                    })
                    line_text.append(w.value)
                text_lines.append(" ".join(line_text))

    full_text = "\n".join(text_lines)

    if words:
        confidences = [w["confidence"] for w in words]
        avg_conf = sum(confidences) / len(confidences)
        lowest_conf = min(confidences)
        low_count = sum(1 for c in confidences if c < CONFIDENCE_THRESHOLD)
    else:
        avg_conf = 0.0
        lowest_conf = 0.0
        low_count = 0

    return {
        "words": words,
        "full_text": full_text,
        "avg_confidence": avg_conf,
        "lowest_confidence": lowest_conf,
        "low_confidence_word_count": low_count,
        # Zero tolerance: flagged the moment ANY word is below threshold,
        # including the empty-OCR case (no words at all is its own failure
        # mode and should also route to the correction queue, not pass silently).
        "flagged": low_count > 0 or not words,
    }


# --------------------------------------------------------------------------
# Ollama pass -> field-level KIE over the OCR'd text
# --------------------------------------------------------------------------

def _run_ollama_kie(text: str) -> dict[str, Any]:
    if len(text) > OLLAMA_MAX_CHARS:
        # Guard from the fix list: don't hand Ollama something big enough
        # to crash/hang it. Truncate rather than skip entirely so short
        # documents still degrade gracefully; log for visibility upstream.
        text = text[:OLLAMA_MAX_CHARS]

    prompt = _KIE_PROMPT.format(fields=json.dumps(TARGET_FIELDS), text=text)

    last_err: Exception | None = None
    for attempt in range(OLLAMA_MAX_RETRIES + 1):
        try:
            resp = requests.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0},
                },
                timeout=120,
            )
            resp.raise_for_status()
            raw = resp.json().get("response", "").strip()
            raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            parsed = json.loads(raw)
            return {k: parsed.get(k) for k in TARGET_FIELDS}
        except (requests.RequestException, json.JSONDecodeError) as exc:
            last_err = exc
            if attempt < OLLAMA_MAX_RETRIES:
                time.sleep(2 * (attempt + 1))
                continue

    # All retries exhausted: return an empty field set rather than raising,
    # so the document still lands in the correction queue instead of
    # failing the whole ingest job.
    return {k: None for k in TARGET_FIELDS} | {"_ollama_error": str(last_err)}


# --------------------------------------------------------------------------
# Public entrypoint
#
# Named for what it does, not for the model it replaces. Signature is
# still keyword-only (file_bytes, filename) matching the shape lilt.py
# used - that part of the interface is worth keeping, the name isn't.
# --------------------------------------------------------------------------

def run_doctr_extraction(*, file_bytes: bytes, filename: str) -> ExtractionResult:
    timer = ExtractionTimer(verbose=VERBOSE).start()

    with timer.stage("doctr_ocr"):
        ocr = _run_doctr(file_bytes, filename)

    with timer.stage("ollama_kie"):
        fields = _run_ollama_kie(ocr["full_text"])

    processing_log = timer.finish()
    if VERBOSE:
        logger.info("Extraction complete filename=%s\n%s", filename, processing_log)

    return ExtractionResult(
        text=ocr["full_text"],
        confidence=round(ocr["avg_confidence"], 4),
        fields=fields,
        ocr_confidence_average=round(ocr["avg_confidence"], 4),
        ocr_confidence_lowest=round(ocr["lowest_confidence"], 4),
        ocr_low_confidence=ocr["flagged"],
        word_boxes=ocr["words"],
        extraction_raw_jsonb={"ocr_text": ocr["full_text"], "fields": fields},
        engine_meta={
            "detection_arch": DETECTION_ARCH,
            "recognition_arch": RECOGNITION_ARCH,
            "low_confidence_word_count": ocr["low_confidence_word_count"],
            "confidence_threshold": CONFIDENCE_THRESHOLD,
        },
        processing_log=processing_log,
    )


def clear_doctr_cache() -> None:
    """Mirrors lilt.py's clear_lilt_cache() - useful for tests and for
    forcing a reload after sync_weights.py pulls a newly promoted
    checkpoint from MinIO without restarting the whole worker process."""
    global _predictor
    _predictor = None
