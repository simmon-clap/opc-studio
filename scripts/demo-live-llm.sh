#!/usr/bin/env bash
# Live LLM smoke test — uses CEO Key from Settings or OPC_CEO_* env vars.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${OPC_PORT:-8765}"
BASE="${OPC_API_BASE:-http://127.0.0.1:${PORT}/api/v1}"

echo "→ Health ($BASE)"
curl -sf "$BASE/health" | head -c 200 || true
echo

read -r CEO_MODEL CEO_PROVIDER CEO_BASE CEO_KEY <<EOF
$(python3 <<PY
import json, urllib.request, os
base = "$BASE"
try:
    with urllib.request.urlopen(f"{base}/roles/config") as r:
        ceo = next(c for c in json.load(r)["data"] if c["roleId"] == "ceo")
    slot = (ceo.get("models") or {}).get("text") or {}
    print(
        slot.get("model") or os.environ.get("OPC_CEO_MODEL", "gpt-4o-mini"),
        slot.get("apiProvider") or os.environ.get("OPC_CEO_PROVIDER", "OpenAI"),
        slot.get("apiBaseUrl") or os.environ.get("OPC_CEO_API_BASE", "https://api.openai.com/v1"),
        "configured" if ceo.get("apiKeyConfigured") else "",
    )
except Exception:
    print(
        os.environ.get("OPC_CEO_MODEL", "gpt-4o-mini"),
        os.environ.get("OPC_CEO_PROVIDER", "OpenAI"),
        os.environ.get("OPC_CEO_API_BASE", "https://api.openai.com/v1"),
        "",
    )
PY
)
EOF

if [[ -n "${OPC_CEO_API_KEY:-}" ]]; then
  echo "→ 写入 CEO Key（来自 OPC_CEO_API_KEY）"
  curl -sf -X PUT "$BASE/roles/config/ceo" \
    -H 'Content-Type: application/json' \
    -d "{\"models\":{\"text\":{\"model\":\"${OPC_CEO_MODEL:-$CEO_MODEL}\",\"apiProvider\":\"${OPC_CEO_PROVIDER:-$CEO_PROVIDER}\",\"apiBaseUrl\":\"${OPC_CEO_API_BASE:-$CEO_BASE}\",\"apiKey\":\"$OPC_CEO_API_KEY\"}}}" \
    | head -c 300 || true
  echo
elif [[ "$CEO_KEY" != "configured" ]]; then
  echo "⚠ CEO 未配置 Key — 请在设置页填写或 export OPC_CEO_API_KEY"
  exit 1
else
  echo "→ 使用已存 CEO 配置: $CEO_MODEL @ $CEO_PROVIDER"
fi

echo "→ Test connection"
TEST_BODY="{\"capability\":\"text\",\"model\":\"${OPC_CEO_MODEL:-$CEO_MODEL}\",\"apiProvider\":\"${OPC_CEO_PROVIDER:-$CEO_PROVIDER}\",\"apiBaseUrl\":\"${OPC_CEO_API_BASE:-$CEO_BASE}\""
if [[ -n "${OPC_CEO_API_KEY:-}" ]]; then
  TEST_BODY+=",\"apiKey\":\"$OPC_CEO_API_KEY\""
fi
TEST_BODY+="}"
curl -sf -X POST "$BASE/roles/config/ceo/test" -H 'Content-Type: application/json' -d "$TEST_BODY" | head -c 400 || true
echo

MARKER="LLM-DEMO-$(date +%s)"
echo "→ CEO brief (live): $MARKER"
curl -sf -X POST "$BASE/ceo/brief" \
  -H 'Content-Type: application/json' \
  -d "{\"text\":\"【${MARKER}】用一句话介绍 Golden Mean Studio 的定位。\"}" \
  | head -c 400 || true
echo

echo "→ 等待 CEO 回复（最多 90s）..."
python3 <<PY
import json, time, urllib.request, sys
BASE = "$BASE"
MARKER = "$MARKER"
deadline = time.time() + 90
while time.time() < deadline:
    with urllib.request.urlopen(f"{BASE}/ceo/thread") as resp:
        thread = json.load(resp)["data"]
    founders = [m for m in thread if MARKER in (m.get("text") or "")]
    if not founders:
        time.sleep(1)
        continue
    f_at = founders[-1].get("at", "")
    for m in reversed(thread):
        if (
            m.get("direction") == "ceo_to_founder"
            and m.get("type") not in ("ack", None)
            and m.get("text") not in ("…", "")
            and (m.get("at") or "") >= f_at
        ):
            print("✓ CEO Live 回复：")
            print(m["text"])
            sys.exit(0)
    time.sleep(2)
print("⚠ 超时 — 检查 dashboard CEO 办公室或服务器日志")
for m in thread[-4:]:
    print("-", m.get("direction"), (m.get("text") or "")[:120])
sys.exit(1)
PY
