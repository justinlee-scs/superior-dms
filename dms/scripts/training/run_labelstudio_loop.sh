#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUTPUT_DIR="${ROOT_DIR}/output"
MODEL_DIR="${OUTPUT_DIR}/models"

echo "Starting Label Studio feedback loop..."
echo "Root: ${ROOT_DIR}"
echo "Output: ${OUTPUT_DIR}"

bash "${ROOT_DIR}/scripts/training/run_training_pipeline.sh"

echo ""
echo "Training complete."
echo "Point the app at the new models (paths below):"
echo "  DOC_CLASS_MODEL_PATH=${MODEL_DIR}/doc_classifier.joblib"
echo "  TAGGER_MODEL_PATH=${MODEL_DIR}/tagger.joblib"
echo "  HANDWRITING_MODEL_PATH=${MODEL_DIR}/handwriting.pt"
echo "  OCR_PROVIDER=trocr_hf"
echo "  TROCR_MODEL_PATH=${MODEL_DIR}/trocr"
echo ""
echo "If your API is already running, restart it after updating env vars."
