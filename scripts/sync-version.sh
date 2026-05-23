#!/usr/bin/env bash
# Sync VERSION file → frontend cache bust, pyproject, health endpoint.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(tr -d '[:space:]' < "$ROOT/VERSION")"

if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$ ]]; then
  echo "Invalid VERSION: $VERSION (expected semver, e.g. 0.9.0)" >&2
  exit 1
fi

INDEX="$ROOT/dashboards/app/index.html"
sed -i '' "s/\?v=[0-9][^\"']*/?v=${VERSION}/g" "$INDEX" 2>/dev/null \
  || sed -i "s/\?v=[0-9][^\"']*/?v=${VERSION}/g" "$INDEX"

PYPROJECT="$ROOT/backend/pyproject.toml"
sed -i '' "s/^version = \".*\"/version = \"${VERSION}\"/" "$PYPROJECT" 2>/dev/null \
  || sed -i "s/^version = \".*\"/version = \"${VERSION}\"/" "$PYPROJECT"

echo "Synced version ${VERSION}"
echo "  - dashboards/app/index.html (?v= cache bust)"
echo "  - backend/pyproject.toml"
