#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PIDFILE="${ROOT}/data/opc-studio.pid"
LABEL="com.opc-studio"

launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null || true

if [ -f "$PIDFILE" ]; then
  pid="$(cat "$PIDFILE")"
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid"
    echo "Stopped daemon pid $pid"
  fi
  rm -f "$PIDFILE"
fi

if lsof -ti :8765 >/dev/null 2>&1; then
  lsof -ti :8765 | xargs kill -9 2>/dev/null || true
  echo "Freed port 8765"
fi
