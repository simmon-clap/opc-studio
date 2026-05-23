#!/usr/bin/env bash
# Pre-release gate: version sync, tests, health contract.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VERSION="$(tr -d '[:space:]' < VERSION)"
echo "== OPC Studio release check v${VERSION} =="

"$ROOT/scripts/sync-version.sh"

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
if ! python3 -c "import fastapi" 2>/dev/null; then
  pip install -q -e backend/
fi

export PYTHONPATH="${PWD}/backend/app"
python3 - <<'PY'
from pathlib import Path
import sys

root = Path(".").resolve()
version = root.joinpath("VERSION").read_text().strip()
from app.config import APP_VERSION

if APP_VERSION != version:
    print(f"APP_VERSION mismatch: config={APP_VERSION} VERSION={version}", file=sys.stderr)
    sys.exit(1)
print(f"APP_VERSION OK: {APP_VERSION}")
PY

pytest backend/tests -q
node --check dashboards/app/js/presentation.js
node --check dashboards/app/js/app.js
node --check dashboards/app/js/api.js

echo ""
echo "Release check passed for v${VERSION}"
echo "Next: git tag v${VERSION} && git push origin v${VERSION}"
