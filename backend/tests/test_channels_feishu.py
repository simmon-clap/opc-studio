"""Feishu channel webhook and settings."""

from __future__ import annotations

import hashlib
import json


def _feishu_sig(timestamp: str, nonce: str, body: bytes, token: str) -> str:
    raw = f"{timestamp}{nonce}{token}{body.decode('utf-8')}"
    return hashlib.sha256(raw.encode()).hexdigest()


def test_feishu_url_verification(client):
    res = client.post(
        "/api/v1/channels/feishu/webhook",
        json={"type": "url_verification", "challenge": "abc123"},
    )
    assert res.status_code == 200
    assert res.json()["challenge"] == "abc123"


def test_feishu_webhook_message(client):
    client.patch(
        "/api/v1/system/settings",
        json={
            "channels": {
                "feishu": {
                    "appId": "cli_test",
                    "verificationToken": "verify-token",
                }
            }
        },
    )
    payload = {
        "header": {"event_type": "im.message.receive_v1"},
        "event": {
            "message": {
                "message_type": "text",
                "content": json.dumps({"text": "飞书渠道测试"}),
                "chat_id": "oc_test_chat",
            },
            "sender": {"sender_id": {"open_id": "ou_test"}},
        },
    }
    body = json.dumps(payload).encode()
    ts = "1700000000"
    nonce = "nonce1"
    sig = _feishu_sig(ts, nonce, body, "verify-token")
    res = client.post(
        "/api/v1/channels/feishu/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Lark-Request-Timestamp": ts,
            "X-Lark-Request-Nonce": nonce,
            "X-Lark-Signature": sig,
        },
    )
    assert res.status_code == 200
    assert res.json()["data"]["channel"] == "feishu"

    status = client.get("/api/v1/channels/status").json()["data"]
    assert status["feishu"]["connected"] is True
