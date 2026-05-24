#!/usr/bin/env bash
# Background daemon (nohup) — works when LaunchAgent cannot access ~/Documents.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
PIDFILE="${ROOT}/data/opc-studio.pid"
LOG_OUT="${ROOT}/data/logs/opc-studio.out.log"
LOG_ERR="${ROOT}/data/logs/opc-studio.err.log"

mkdir -p data/logs

if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  echo "Already running (pid $(cat "$PIDFILE"))"
  exit 0
fi

if [ -f .env ]; then
  # shellcheck disable=SC1091
  set -a && source .env && set +a
fi

HOST="${OPC_HOST:-127.0.0.1}"
PORT="${OPC_PORT:-8765}"
export PYTHONPATH="${ROOT}/backend/app"

nohup "${ROOT}/.venv/bin/uvicorn" app.main:app --host "$HOST" --port "$PORT" \
  >>"$LOG_OUT" 2>>"$LOG_ERR" &
echo $! >"$PIDFILE"
echo "Started pid $(cat "$PIDFILE") → http://${HOST}:${PORT}/dashboards/app/"
