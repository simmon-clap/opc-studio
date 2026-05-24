"""Deliver CEO replies to external channels (WeChat via OpenClaw Gateway)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.presentation.settings import get_system_settings
from app.services.channel_state import _now_iso, wechat_settings

logger = logging.getLogger(__name__)

PROBE_TIMEOUT = 5.0
SEND_TIMEOUT = 15.0


def _last_wechat_recipient(dashboard: dict[str, Any]) -> str | None:
    meta = dashboard.get("meta") or {}
    if meta.get("lastWechatSenderId"):
        return str(meta["lastWechatSenderId"])
    thread = dashboard.get("ceoThread") or []
    for msg in reversed(thread):
        if msg.get("direction") == "founder_to_ceo" and msg.get("channel") == "wechat":
            sid = msg.get("senderId")
            if sid:
                return str(sid)
    wc = (dashboard.get("channels") or {}).get("wechat") or {}
    if wc.get("lastSenderId"):
        return str(wc["lastSenderId"])
    return None


def latest_wechat_reply_text(dashboard: dict[str, Any]) -> str | None:
    thread = dashboard.get("ceoThread") or []
    for msg in reversed(thread):
        if msg.get("direction") != "ceo_to_founder":
            continue
        if msg.get("type") == "ack":
            continue
        if msg.get("channel") != "wechat":
            continue
        text = (msg.get("text") or "").strip()
        if text and text != "…":
            return text
    return None


async def probe_wechat_gateway(cfg: dict[str, Any]) -> dict[str, Any]:
    """Ping OpenClaw or webhook endpoint; return {ok, mode, detail}."""
    mode = (cfg.get("outboundMode") or "openclaw").strip()
    headers: dict[str, str] = {"Content-Type": "application/json"}

    if mode == "webhook":
        url = (cfg.get("webhookUrl") or "").strip()
        if not url:
            return {"ok": False, "mode": mode, "detail": "webhookUrl 未配置"}
        token = (cfg.get("webhookToken") or "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            async with httpx.AsyncClient(timeout=PROBE_TIMEOUT) as client:
                res = await client.post(url, json={"message": "OPC ping"}, headers=headers)
            ok = res.status_code < 400
            return {"ok": ok, "mode": mode, "status": res.status_code, "detail": res.text[:200]}
        except httpx.HTTPError as exc:
            return {"ok": False, "mode": mode, "detail": str(exc)}

    base = (cfg.get("gatewayUrl") or "").strip().rstrip("/")
    if not base:
        return {"ok": False, "mode": mode, "detail": "gatewayUrl 未配置"}
    token = (cfg.get("gatewayToken") or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"{base}/openclaw/getupdates"
    try:
        async with httpx.AsyncClient(timeout=PROBE_TIMEOUT) as client:
            res = await client.post(url, json={}, headers=headers)
        ok = res.status_code < 400
        return {"ok": ok, "mode": mode, "status": res.status_code, "detail": "openclaw reachable"}
    except httpx.HTTPError as exc:
        return {"ok": False, "mode": mode, "detail": str(exc)}


async def send_wechat_text(
    cfg: dict[str, Any],
    text: str,
    *,
    recipient_id: str | None = None,
) -> dict[str, Any]:
    body = (text or "").strip()
    if not body:
        return {"ok": False, "detail": "empty message"}
    mode = (cfg.get("outboundMode") or "openclaw").strip()
    headers: dict[str, str] = {"Content-Type": "application/json"}

    if mode == "webhook":
        url = (cfg.get("webhookUrl") or "").strip()
        token = (cfg.get("webhookToken") or "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        payload: dict[str, Any] = {"message": body}
        if recipient_id:
            payload["userId"] = recipient_id
        async with httpx.AsyncClient(timeout=SEND_TIMEOUT) as client:
            res = await client.post(url, json=payload, headers=headers)
        ok = res.status_code < 400
        return {"ok": ok, "mode": mode, "status": res.status_code, "detail": res.text[:300]}

    base = (cfg.get("gatewayUrl") or "").strip().rstrip("/")
    token = (cfg.get("gatewayToken") or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    msg: dict[str, Any] = {
        "item_list": [{"type": 1, "text_item": {"text": body}}],
    }
    if recipient_id:
        msg["to_user_id"] = recipient_id
    url = f"{base}/openclaw/sendmessage"
    async with httpx.AsyncClient(timeout=SEND_TIMEOUT) as client:
        res = await client.post(url, json={"msg": msg}, headers=headers)
    ok = res.status_code < 400
    return {"ok": ok, "mode": mode, "status": res.status_code, "detail": res.text[:300]}


async def deliver_wechat_reply_for_dashboard(dashboard: dict[str, Any]) -> dict[str, Any] | None:
    cfg = wechat_settings(dashboard)
    if not _wechat_outbound_enabled(cfg):
        return None
    text = latest_wechat_reply_text(dashboard)
    if not text:
        return None
    recipient = _last_wechat_recipient(dashboard)
    try:
        result = await send_wechat_text(cfg, text, recipient_id=recipient)
        if not result.get("ok"):
            logger.warning("WeChat outbound failed: %s", result)
        return result
    except httpx.HTTPError as exc:
        logger.exception("WeChat outbound error")
        return {"ok": False, "detail": str(exc)}


def _wechat_outbound_enabled(cfg: dict[str, Any]) -> bool:
    if cfg.get("enabled") is False:
        return False
    if cfg.get("outboundEnabled") is False:
        return False
    mode = cfg.get("outboundMode") or "openclaw"
    if mode == "webhook":
        return bool((cfg.get("webhookUrl") or "").strip())
    return bool((cfg.get("gatewayUrl") or "").strip())


async def deliver_wechat_reply_from_session() -> dict[str, Any] | None:
    from app.db import session_scope
    from app.services.dashboard_store import get_dashboard, mutate

    with session_scope() as session:
        dashboard = get_dashboard(session)
        result = await deliver_wechat_reply_for_dashboard(dashboard)
        if result and result.get("ok"):
            with mutate(session) as dash:
                wc = dash.setdefault("channels", {}).setdefault("wechat", {})
                wc["lastOutboundAt"] = _now_iso()
        return result
