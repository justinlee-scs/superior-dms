#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 /absolute/path/to/pdfs"
  exit 1
fi

INPUT_DIR="$1"
ROOT="/home/justinlee/.LINUXPRACTICE/dms"

python3 "${ROOT}/scripts/training/export_pdf_images.py" \
  --input-dir "${INPUT_DIR}" \
  --output-dir "${ROOT}/output/training/ocr_images" \
  --tasks "${ROOT}/output/training/ocr_tasks.json"

python3 - <<'PY'
import json
from pathlib import Path

src = Path('/home/justinlee/.LINUXPRACTICE/dms/output/training/ocr_tasks.json')
data = json.loads(src.read_text())
for task in data:
    img = task.get('data', {}).get('image')
    if isinstance(img, str):
        name = img.split('/')[-1]
        task['data']['image'] = f'http://localhost:8089/{name}'
src.write_text(json.dumps(data, ensure_ascii=False, indent=2))
print('Updated ocr_tasks.json to use http://localhost:8089/ URLs')
PY

python3 "${ROOT}/scripts/training/export_text_tasks.py" \
  --input-dir "${INPUT_DIR}" \
  --output "${ROOT}/output/training/text_tasks.json"

echo "Ready to import:"
echo "- ${ROOT}/output/training/text_tasks.json"
echo "- ${ROOT}/output/training/ocr_tasks.json"
