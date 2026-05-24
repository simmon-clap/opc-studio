"""Detect local OpenClaw install for WeChat ClawBot setup."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

OPENCLAW_CONFIG = Path.home() / ".openclaw" / "openclaw.json"
CLAWBOT_CLI = "npx -y @tencent-weixin/openclaw-weixin-cli@latest install"
LOGIN_CMD = "openclaw channels login --channel openclaw-weixin"


def _read_openclaw_config() -> dict[str, Any]:
    if not OPENCLAW_CONFIG.is_file():
        return {}
    try:
        raw = json.loads(OPENCLAW_CONFIG.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def detect_openclaw() -> dict[str, Any]:
    """Return local OpenClaw / ClawBot environment hints for the settings UI."""
    cli = shutil.which("openclaw")
    version: str | None = None
    if cli:
        try:
            proc = subprocess.run(
                [cli, "--version"],
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
            version = (proc.stdout or proc.stderr or "").strip() or None
        except (OSError, subprocess.TimeoutExpired):
            version = None

    cfg = _read_openclaw_config()
    gateway = cfg.get("gateway") if isinstance(cfg.get("gateway"), dict) else {}
    env_port = os.environ.get("OPENCLAW_GATEWAY_PORT", "").strip()
    try:
        gateway_port = int(env_port) if env_port else int(gateway.get("port") or 18789)
    except (TypeError, ValueError):
        gateway_port = 18789

    weixin_cfg = cfg.get("channels", {}).get("openclaw-weixin", {})
    if not isinstance(weixin_cfg, dict):
        weixin_cfg = {}
    plugin_enabled = bool(
        cfg.get("plugins", {})
        .get("entries", {})
        .get("openclaw-weixin", {})
        .get("enabled")
    )

    return {
        "openclawInstalled": bool(cli),
        "openclawPath": cli,
        "openclawVersion": version,
        "configPath": str(OPENCLAW_CONFIG) if OPENCLAW_CONFIG.is_file() else None,
        "gatewayPort": gateway_port,
        "pluginEnabled": plugin_enabled,
        "hasWeixinChannelConfig": bool(weixin_cfg),
        "clawbotCli": CLAWBOT_CLI,
        "loginCmd": LOGIN_CMD,
        "suggestedGatewayUrls": [
            "http://127.0.0.1:9200",
            f"http://127.0.0.1:{gateway_port}",
        ],
        "wechatEntry": "微信 → 我 → 设置 → 插件 → ClawBot",
    }
