#!/usr/bin/env bash
set -euo pipefail

python3 /home/justinlee/.LINUXPRACTICE/dms/scripts/serve_ocr_images.py \
  --dir /home/justinlee/.LINUXPRACTICE/dms/output/training/ocr_images \
  --port 8089
