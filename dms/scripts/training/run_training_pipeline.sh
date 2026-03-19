#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUTPUT_DIR="${ROOT_DIR}/output"
TRAIN_DIR="${OUTPUT_DIR}/training"
MODEL_DIR="${OUTPUT_DIR}/models"

mkdir -p "${OUTPUT_DIR}" "${TRAIN_DIR}" "${MODEL_DIR}"

echo "Exporting Label Studio tasks..."
python "${ROOT_DIR}/scripts/training/export_labelstudio.py" \
  --output "${OUTPUT_DIR}/labelstudio_export.json"

echo "Preparing datasets..."
python "${ROOT_DIR}/scripts/training/prepare_labelstudio.py" \
  --input "${OUTPUT_DIR}/labelstudio_export.json" \
  --output-dir "${TRAIN_DIR}"

echo "Training document classifier..."
python "${ROOT_DIR}/scripts/training/train_doc_classifier.py" \
  --input "${TRAIN_DIR}/doc_class.csv" \
  --output "${MODEL_DIR}/doc_classifier.joblib"

echo "Training tagger..."
python "${ROOT_DIR}/scripts/training/train_tagger.py" \
  --input "${TRAIN_DIR}/tags.csv" \
  --output "${MODEL_DIR}/tagger.joblib"

echo "Training handwriting classifier..."
python "${ROOT_DIR}/scripts/training/train_handwriting.py" \
  --input "${TRAIN_DIR}/handwriting.csv" \
  --output "${MODEL_DIR}/handwriting.pt"

if [[ "${SKIP_TROCR:-false}" == "true" ]]; then
  echo "Skipping TrOCR training (SKIP_TROCR=true)."
  exit 0
fi

echo "Training TrOCR (CPU, may be slow)..."
python "${ROOT_DIR}/scripts/training/train_trocr.py" \
  --input "${TRAIN_DIR}/trocr.jsonl" \
  --output "${MODEL_DIR}/trocr"
