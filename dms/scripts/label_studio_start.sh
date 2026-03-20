#!/usr/bin/env bash
set -euo pipefail
cd /home/justinlee/.LINUXPRACTICE/dms

PORT=8800
export LOCAL_FILES_SERVING_ENABLED=true
export LOCAL_FILES_DOCUMENT_ROOT=/home/justinlee/.LINUXPRACTICE/dms

LS_ENV_FILE="/home/justinlee/.local/share/label-studio/.env"
mkdir -p "$(dirname "${LS_ENV_FILE}")"
touch "${LS_ENV_FILE}"

if grep -q "^LOCAL_FILES_SERVING_ENABLED=" "${LS_ENV_FILE}"; then
  sed -i "s/^LOCAL_FILES_SERVING_ENABLED=.*/LOCAL_FILES_SERVING_ENABLED=true/" "${LS_ENV_FILE}"
else
  echo "LOCAL_FILES_SERVING_ENABLED=true" >> "${LS_ENV_FILE}"
fi

if grep -q "^LOCAL_FILES_DOCUMENT_ROOT=" "${LS_ENV_FILE}"; then
  sed -i "s|^LOCAL_FILES_DOCUMENT_ROOT=.*|LOCAL_FILES_DOCUMENT_ROOT=/home/justinlee/.LINUXPRACTICE/dms|" "${LS_ENV_FILE}"
else
  echo "LOCAL_FILES_DOCUMENT_ROOT=/home/justinlee/.LINUXPRACTICE/dms" >> "${LS_ENV_FILE}"
fi

python3 - <<'PY'
import socket

port = 8800
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    sock.bind(("127.0.0.1", port))
except OSError:
    raise SystemExit(
        f"Port {port} is already in use. Stop the process using it, then retry."
    )
finally:
    sock.close()
PY

env DEBUG=false LATEST_VERSION_CHECK=false SENTRY_DSN= \
  ./.venv/bin/label-studio start --port "${PORT}" --no-browser
