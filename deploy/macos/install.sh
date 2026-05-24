#!/usr/bin/env bash
# Deploy OPC Studio on macOS: LaunchAgent when allowed, else nohup daemon.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
PLIST_SRC="${ROOT}/deploy/macos/com.opc-studio.plist"
PLIST_DST="${HOME}/Library/LaunchAgents/com.opc-studio.plist"
LABEL="com.opc-studio"

echo "== OPC Studio macOS deploy =="

if [ ! -f .env ]; then
  echo "Missing .env — copy from .env.example and set OPC_SECRET_KEY first." >&2
  exit 1
fi

# shellcheck disable=SC1091
set -a && source .env && set +a
HOST="${OPC_HOST:-127.0.0.1}"
PORT="${OPC_PORT:-8765}"
DATA_DIR="${OPC_DATA_DIR:-./data}"
SECRET="${OPC_SECRET_KEY:-}"

if [ -z "$SECRET" ]; then
  echo "OPC_SECRET_KEY is empty in .env" >&2
  exit 1
fi

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -e backend/

mkdir -p data/logs
chmod +x "${ROOT}/deploy/macos/"*.sh

"${ROOT}/deploy/macos/stop.sh" 2>/dev/null || true

health_ok() {
  curl -sf "http://${HOST}:${PORT}/api/v1/health" >/dev/null 2>&1
}

# Try LaunchAgent (direct uvicorn — avoids shell script TCC issues)
sed -e "s|__ROOT__|${ROOT}|g" \
    -e "s|__HOST__|${HOST}|g" \
    -e "s|__PORT__|${PORT}|g" \
    -e "s|__OPC_DATA_DIR__|${DATA_DIR}|g" \
    -e "s|__OPC_SECRET_KEY__|${SECRET}|g" \
    "$PLIST_SRC" > "$PLIST_DST"

launchctl bootstrap "gui/$(id -u)" "$PLIST_DST" 2>/dev/null || true
launchctl enable "gui/$(id -u)/${LABEL}" 2>/dev/null || true
launchctl kickstart -k "gui/$(id -u)/${LABEL}" 2>/dev/null || true

sleep 3
if health_ok; then
  echo "✓ LaunchAgent OK → http://${HOST}:${PORT}/dashboards/app/"
  exit 0
fi

echo "LaunchAgent unavailable (common in ~/Documents) — starting nohup daemon…" >&2
: > "${ROOT}/data/logs/opc-studio.err.log"
"${ROOT}/deploy/macos/daemon.sh"
sleep 2

if health_ok; then
  echo "✓ Daemon OK → http://${HOST}:${PORT}/dashboards/app/"
  echo "  Logs: data/logs/opc-studio.{out,err}.log"
  echo "  Stop: ./deploy/macos/stop.sh"
  exit 0
fi

echo "⚠ Health check failed — see data/logs/opc-studio.err.log" >&2
tail -20 "${ROOT}/data/logs/opc-studio.err.log" 2>/dev/null || true
exit 1
