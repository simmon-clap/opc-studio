"""WeChat channel: ingress auth, state, outbound, settings."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch


def test_channel_inbound_wechat_records_sender(client):
    res = client.post(
        "/api/v1/channels/inbound",
        json={
            "channel": "wechat",
            "text": "渠道测试消息",
            "senderId": "wx-user-001",
            "senderName": "Founder",
        },
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["channel"] == "wechat"

    status = client.get("/api/v1/channels/status").json()["data"]
    assert status["wechat"]["connected"] is True

    thread = client.get("/api/v1/ceo/thread").json()["data"]
    founder = [m for m in thread if m.get("text") == "渠道测试消息"][0]
    assert founder.get("channel") == "wechat"
    assert founder.get("senderId") == "wx-user-001"


def test_channels_setup_includes_bridge(client):
    res = client.get("/api/v1/channels/setup")
    assert res.status_code == 200
    setup = res.json()["data"]
    assert "clawbot" in setup["wechat"]
    assert "bridgeStart" in setup["wechat"]["opcBridge"]
    assert setup["wechat"]["opcBridge"]["bridgeDir"] == "bridge/openclaw-opc"


def test_patch_wechat_channel_settings(client):
    res = client.patch(
        "/api/v1/system/settings",
        json={
            "channels": {
                "wechat": {
                    "gatewayUrl": "http://127.0.0.1:9200",
                    "gatewayToken": "test-token-xyz",
                    "outboundMode": "openclaw",
                }
            }
        },
    )
    assert res.status_code == 200
    wc = res.json()["data"]["channels"]["wechat"]
    assert wc["gatewayUrl"] == "http://127.0.0.1:9200"
    assert wc["gatewayToken"]["masked"].endswith("xyz")


def test_inbound_auth_when_secret_configured(client, monkeypatch):
    monkeypatch.setattr("app.services.channel_auth.CHANNEL_SECRET", "bridge-secret")
    monkeypatch.setattr("app.api.channels.CHANNEL_SECRET", "bridge-secret")
    res = client.post(
        "/api/v1/channels/inbound",
        json={"channel": "wechat", "text": "需要鉴权"},
    )
    assert res.status_code == 401

    res2 = client.post(
        "/api/v1/channels/inbound",
        json={"channel": "wechat", "text": "鉴权通过"},
        headers={"X-OPC-Channel-Token": "bridge-secret"},
    )
    assert res2.status_code == 200


def test_wechat_detect_endpoint(client):
    res = client.get("/api/v1/channels/wechat/detect")
    assert res.status_code == 200
    body = res.json()["data"]
    assert "openclawInstalled" in body
    assert body["clawbotCli"].startswith("npx")


def test_channels_setup_has_clawbot_steps(client):
    res = client.get("/api/v1/channels/setup")
    steps = res.json()["data"]["wechat"]["clawbot"]["steps"]
    assert len(steps) >= 3
    assert steps[0]["command"].startswith("npx")


def test_wechat_outbound_send_mock():
    from app.services.channel_outbound import send_wechat_text

    cfg = {
        "outboundMode": "openclaw",
        "gatewayUrl": "http://127.0.0.1:9200",
        "gatewayToken": "tok",
    }
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.text = '{"ok":true}'

    async def _run():
        with patch("app.services.channel_outbound.httpx.AsyncClient") as mock_client:
            instance = mock_client.return_value.__aenter__.return_value
            instance.post = AsyncMock(return_value=mock_resp)
            result = await send_wechat_text(cfg, "CEO 回复测试", recipient_id="wx-u1")
        assert result["ok"] is True
        instance.post.assert_called_once()
        call_args = instance.post.call_args
        assert "openclaw/sendmessage" in call_args[0][0]
        assert call_args[1]["json"]["msg"]["to_user_id"] == "wx-u1"

    asyncio.run(_run())


def test_wechat_test_endpoint_probe(client):
    mock_probe = AsyncMock(return_value={"ok": True, "mode": "openclaw"})
    with patch("app.api.channels.probe_wechat_gateway", mock_probe):
        res = client.post("/api/v1/channels/wechat/test", json={"text": "ping"})
    assert res.status_code == 200
    assert res.json()["data"]["probe"]["ok"] is True
