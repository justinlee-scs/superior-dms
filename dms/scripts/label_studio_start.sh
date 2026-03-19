#!/usr/bin/env bash
set -euo pipefail
cd /home/justinlee/.LINUXPRACTICE/dms

PORT=8800

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
