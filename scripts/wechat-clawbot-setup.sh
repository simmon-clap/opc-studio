#!/usr/bin/env bash
# 官方 ClawBot 微信绑定 — 与 OPC Studio 配合使用
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== 微信 ClawBot 绑定（官方流程）==="
echo ""
echo "① 安装 OpenClaw 微信插件并在终端扫码"
echo "   （终端会显示二维码，用微信扫描确认）"
echo ""
npx -y @tencent-weixin/openclaw-weixin-cli@latest install

echo ""
echo "② 若终端未出码，可手动执行："
echo "   openclaw channels login --channel openclaw-weixin"
echo ""
echo "③ 或在手机微信：我 → 设置 → 插件 → ClawBot → 扫码"
echo ""
echo "④ 要让微信消息进入 OPC CEO，另开终端运行 Bridge："
echo "   cd bridge/openclaw-opc && npm install && npm start"
echo ""
echo "OPC Studio: http://127.0.0.1:8765/dashboards/app/ → 设置 → 渠道"
