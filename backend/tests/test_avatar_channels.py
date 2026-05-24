"""Avatar upload and channel ingress tests."""

from __future__ import annotations

import base64

TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def test_upload_role_avatar(client):
    client.post(
        "/api/v1/roles/registry",
        json={"id": "brand", "name": "苏见", "capabilities": ["text"]},
    )
    res = client.post(
        "/api/v1/roles/brand/avatar",
        files={"file": ("avatar.png", TINY_PNG, "image/png")},
    )
    assert res.status_code == 200
    body = res.json()["data"]
    assert body["avatar"].startswith("/assets/uploads/avatars/brand")
    assert body["role"]["avatar"] == body["avatar"]

    cfg = client.get("/api/v1/roles/registry").json()["data"]
    brand = next(r for r in cfg if r["id"] == "brand")
    assert brand["avatar"] == body["avatar"]


def test_resolve_avatar_url_mismatch_ext():
    from app.services.avatar_storage import AVATAR_DIR, resolve_avatar_url

    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    (AVATAR_DIR / "brand.png").write_bytes(TINY_PNG)
    url = resolve_avatar_url("brand", "/assets/uploads/avatars/brand.jpg")
    assert url == "/assets/uploads/avatars/brand.png"


def test_channel_inbound_wechat(client):
    res = client.post(
        "/api/v1/channels/inbound",
        json={"channel": "wechat", "text": "渠道测试消息", "senderName": "Founder"},
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["channel"] == "wechat"
    thread = client.get("/api/v1/ceo/thread").json()["data"]
    assert any(m.get("text") == "渠道测试消息" and m.get("channel") == "wechat" for m in thread)


def test_channels_setup(client):
    res = client.get("/api/v1/channels/setup")
    assert res.status_code == 200
    setup = res.json()["data"]
    assert "clawbot" in setup["wechat"]
    assert "inboundUrl" in setup["wechat"]["opcBridge"]
    assert setup["wechat"]["clawbot"]["cli"].startswith("npx")
