"""Unified channel message ingress → CEO thread."""

from __future__ import annotations

from typing import Any

from app.services.channel_state import record_wechat_inbound
from app.services.state_machines import submit_ceo_brief

ALLOWED_CHANNELS = frozenset({"web", "wechat", "feishu"})


def ingest_channel_message(
    dashboard: dict[str, Any],
    *,
    channel: str,
    text: str,
    sender_id: str | None = None,
    sender_name: str | None = None,
) -> dict[str, Any]:
    ch = channel if channel in ALLOWED_CHANNELS else "web"
    body = text.strip()
    if not body:
        raise ValueError("EMPTY_MESSAGE")
    result = submit_ceo_brief(dashboard, body, channel=ch)
    thread = dashboard.get("ceoThread", [])
    if thread and len(thread) >= 2:
        founder_msg = thread[-2]
        if sender_id:
            founder_msg["senderId"] = sender_id
        if sender_name:
            founder_msg["senderName"] = sender_name
        reply_msg = thread[-1]
        reply_msg["channel"] = ch
        if sender_id:
            reply_msg["recipientId"] = sender_id
    if ch == "wechat":
        record_wechat_inbound(
            dashboard, sender_id=sender_id, sender_name=sender_name
        )
    return result
