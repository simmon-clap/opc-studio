"""Channel connection state derived from config + activity (not seed mock)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.presentation.settings import get_system_settings

INBOUND_ACTIVE_HOURS = 168  # 7 days


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def wechat_settings(dashboard: dict[str, Any]) -> dict[str, Any]:
    return (get_system_settings(dashboard, masked=False).get("channels") or {}).get("wechat") or {}


def feishu_settings(dashboard: dict[str, Any]) -> dict[str, Any]:
    return (get_system_settings(dashboard, masked=False).get("channels") or {}).get("feishu") or {}


def record_feishu_inbound(
    dashboard: dict[str, Any],
    *,
    sender_id: str | None,
    chat_id: str | None,
) -> None:
    channels = dashboard.setdefault("channels", {})
    fs = channels.setdefault("feishu", {"label": "飞书"})
    fs["lastInboundAt"] = _now_iso()
    fs["lastWebhookAt"] = fs["lastInboundAt"]
    fs["connected"] = True
    if sender_id:
        fs["lastSenderId"] = sender_id
    if chat_id:
        fs["lastChatId"] = chat_id


def record_wechat_inbound(
    dashboard: dict[str, Any],
    *,
    sender_id: str | None,
    sender_name: str | None,
) -> None:
    channels = dashboard.setdefault("channels", {})
    wc = channels.setdefault("wechat", {})
    wc["label"] = wc.get("label") or "微信"
    wc["lastInboundAt"] = _now_iso()
    wc["connected"] = True
    if sender_id:
        wc["lastSenderId"] = sender_id
    if sender_name:
        wc["lastSenderName"] = sender_name
    meta = dashboard.setdefault("meta", {})
    if sender_id:
        meta["lastWechatSenderId"] = sender_id


def _wechat_configured(cfg: dict[str, Any]) -> bool:
    if cfg.get("enabled") is False:
        return False
    mode = cfg.get("outboundMode") or "openclaw"
    if mode == "webhook":
        return bool((cfg.get("webhookUrl") or "").strip())
    return bool((cfg.get("gatewayUrl") or "").strip())


def _wechat_recent_inbound(wc: dict[str, Any]) -> bool:
    last = _parse_iso(wc.get("lastInboundAt"))
    if not last:
        return False
    return datetime.now(timezone.utc) - last.astimezone(timezone.utc) < timedelta(
        hours=INBOUND_ACTIVE_HOURS
    )


def sync_channel_status(dashboard: dict[str, Any]) -> dict[str, Any]:
    """Refresh dashboard.channels.*.connected from real signals."""
    channels = dashboard.setdefault("channels", {})
    wc_cfg = wechat_settings(dashboard)
    wc = channels.setdefault("wechat", {"label": "微信"})
    wc["configured"] = _wechat_configured(wc_cfg)
    wc["connected"] = bool(
        _wechat_recent_inbound(wc) or wc.get("lastProbeOk") is True
    )

    fs_cfg = feishu_settings(dashboard)
    fs = channels.setdefault("feishu", {"label": "飞书"})
    fs["configured"] = bool((fs_cfg.get("appId") or "").strip())
    fs["connected"] = bool(fs.get("lastWebhookAt")) and fs["configured"]

    web = channels.setdefault("web", {"label": "Web"})
    web["connected"] = True
    return channels
