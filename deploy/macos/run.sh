#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if [ -f .env ]; then
  # shellcheck disable=SC1091
  set -a && source .env && set +a
fi

HOST="${OPC_HOST:-127.0.0.1}"
PORT="${OPC_PORT:-8765}"
export PYTHONPATH="${ROOT}/backend/app"
exec "${ROOT}/.venv/bin/uvicorn" app.main:app --host "$HOST" --port "$PORT"
