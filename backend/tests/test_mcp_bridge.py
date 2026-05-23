"""Epic 4 — MCP tests."""

from __future__ import annotations


def test_mcp_connection_crud(client):
    res = client.post(
        "/api/v1/mcp/connections",
        json={
            "id": "image_gen_local",
            "label": "本地图像 MCP",
            "command": ["npx", "-y", "@example/image-mcp"],
            "capabilities": ["image"],
            "allowedRoles": ["brand"],
        },
    )
    assert res.status_code == 200
    health = client.post("/api/v1/mcp/connections/image_gen_local/health")
    assert health.status_code == 200
    assert health.json()["data"]["health"] == "ok"


def test_mcp_list(client):
    client.post(
        "/api/v1/mcp/connections",
        json={"id": "test_mcp", "label": "Test", "capabilities": ["text"]},
    )
    items = client.get("/api/v1/mcp/connections").json()["data"]
    assert any(c["id"] == "test_mcp" for c in items)
