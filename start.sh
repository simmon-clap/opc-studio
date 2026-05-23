#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [ -f .env ]; then
  # shellcheck disable=SC1091
  set -a && source .env && set +a
fi

PORT="${OPC_PORT:-${PORT:-8765}}"
HOST="${OPC_HOST:-127.0.0.1}"
VERSION="$(tr -d '[:space:]' < VERSION 2>/dev/null || echo dev)"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -e backend/ || echo "⚠ pip install 跳过（沿用已有 venv）；若 API 405/404 请手动 pip install -e backend/ 后重启"

export PYTHONPATH="${PWD}/backend/app"
echo "Golden Mean Studio v${VERSION}"
echo "→ http://${HOST}:${PORT}/dashboards/app/"
echo "→ API http://${HOST}:${PORT}/docs"
echo "按 Ctrl+C 停止"
exec uvicorn app.main:app --host "$HOST" --port "$PORT"
