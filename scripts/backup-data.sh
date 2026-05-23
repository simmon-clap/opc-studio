#!/usr/bin/env bash
# Backup runtime data (SQLite + projects + uploads). Safe to run while app is stopped.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ -f .env ]; then
  # shellcheck disable=SC1091
  set -a && source .env && set +a
fi

DATA_DIR="${OPC_DATA_DIR:-./data}"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="${ROOT}/backups"
ARCHIVE="${BACKUP_DIR}/opc-data-${STAMP}.tar.gz"

mkdir -p "$BACKUP_DIR"

if [ ! -d "$DATA_DIR" ]; then
  echo "No data directory: $DATA_DIR" >&2
  exit 1
fi

tar czf "$ARCHIVE" -C "$(dirname "$DATA_DIR")" "$(basename "$DATA_DIR")"
echo "Backup written: $ARCHIVE"
du -h "$ARCHIVE"
