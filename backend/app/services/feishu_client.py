"""Feishu/Lark bot — tenant token, webhook verify, send message."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_TOKEN_CACHE: dict[str, Any] = {"token": "", "expires_at": 0.0}


def verify_feishu_signature(
    timestamp: str, nonce: str, body: bytes, encrypt_key: str, signature: str
) -> bool:
    if not encrypt_key:
        return True
    raw = f"{timestamp}{nonce}{encrypt_key}{body.decode('utf-8', errors='replace')}"
    digest = hashlib.sha256(raw.encode()).hexdigest()
    return digest == signature


async def get_tenant_access_token(app_id: str, app_secret: str) -> str:
    now = time.time()
    if _TOKEN_CACHE.get("token") and _TOKEN_CACHE.get("expires_at", 0) > now + 60:
        return str(_TOKEN_CACHE["token"])
    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": app_id, "app_secret": app_secret},
        )
        data = res.json()
    if data.get("code") != 0:
        raise RuntimeError(data.get("msg") or "feishu token failed")
    token = data["tenant_access_token"]
    _TOKEN_CACHE["token"] = token
    _TOKEN_CACHE["expires_at"] = now + int(data.get("expire", 7200))
    return token


def parse_feishu_message_event(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Extract text + sender from im.message.receive_v1."""
    header = payload.get("header") or {}
    if header.get("event_type") != "im.message.receive_v1":
        return None
    event = payload.get("event") or {}
    message = event.get("message") or {}
    if message.get("message_type") != "text":
        return None
    try:
        content = json.loads(message.get("content") or "{}")
        text = (content.get("text") or "").strip()
    except json.JSONDecodeError:
        text = (message.get("content") or "").strip()
    if not text:
        return None
    sender = event.get("sender") or {}
    sender_id = (sender.get("sender_id") or {}).get("open_id") or sender.get("open_id")
    chat_id = message.get("chat_id")
    return {
        "text": text,
        "senderId": sender_id,
        "chatId": chat_id,
        "messageId": message.get("message_id"),
    }


async def send_feishu_text(cfg: dict[str, Any], text: str, *, chat_id: str | None) -> dict[str, Any]:
    app_id = (cfg.get("appId") or "").strip()
    app_secret = (cfg.get("appSecret") or "").strip()
    if not app_id or not app_secret:
        return {"ok": False, "detail": "飞书 App ID/Secret 未配置"}
    target = chat_id or (cfg.get("defaultChatId") or "").strip()
    if not target:
        return {"ok": False, "detail": "缺少 chat_id"}
    token = await get_tenant_access_token(app_id, app_secret)
    body = {
        "receive_id": target,
        "msg_type": "text",
        "content": json.dumps({"text": text[:4000]}, ensure_ascii=False),
    }
    receive_type = cfg.get("receiveIdType") or "chat_id"
    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.post(
            f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={receive_type}",
            headers={"Authorization": f"Bearer {token}"},
            json=body,
        )
    data = res.json()
    ok = res.status_code < 400 and data.get("code") == 0
    return {"ok": ok, "status": res.status_code, "detail": data.get("msg") or str(data)[:200]}
