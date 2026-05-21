#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PORT="${PORT:-8765}"
echo "OPC Studio Mock 看板 → http://localhost:${PORT}/dashboards/app/"
echo "架构讨论稿 → http://localhost:${PORT}/architecture.html"
echo "按 Ctrl+C 停止"
exec python3 -m http.server "$PORT"
