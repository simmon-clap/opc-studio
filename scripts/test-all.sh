#!/usr/bin/env bash
# Full test suite + API smoke checks (server optional for smoke).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE="${OPC_API_BASE:-http://127.0.0.1:8787/api/v1}"

echo "=== Backend pytest (full) ==="
cd "$ROOT/backend"
pytest -q --tb=short
echo "✓ pytest passed"

echo ""
echo "=== API smoke (requires ./start.sh on :8787) ==="
if curl -sf "$BASE/health" >/dev/null 2>&1; then
  curl -sf "$BASE/health" | head -c 120 && echo
  curl -sf "$BASE/dashboard" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['ok']; print('dashboard keys:', len(d['data']))"
  curl -sf "$BASE/channels/status" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['ok']; print('channels ok')"
  curl -sf "$BASE/tools" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['ok']; print('tools:', len(d['data']))"
  curl -sf "$BASE/skill-chains" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['ok']; print('skill-chains ok')"
  curl -sf "$BASE/meta/skill-routes" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['ok']; print('skill-routes ok')"
  curl -sf "$BASE/pulse/status" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['ok']; print('pulse ok')"
  echo "✓ API smoke passed"
else
  echo "⚠ Server not running at $BASE — skip smoke (run ./start.sh first)"
fi

echo ""
echo "=== All automated checks done ==="
