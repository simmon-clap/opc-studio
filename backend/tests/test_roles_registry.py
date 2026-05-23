"""Epic 1 — role registry & settings domain tests."""

from __future__ import annotations


def test_dashboard_has_registry_domains(client):
    res = client.get("/api/v1/dashboard")
    assert res.status_code == 200
    data = res.json()["data"]
    assert "roleRegistry" in data
    assert "roleProfiles" in data
    assert "systemSettings" in data
    roles = data["roleRegistry"]["roles"]
    ids = {r["id"] for r in roles}
    assert ids == {"ceo", "product", "legal", "dev", "ops"}
    assert "brand" not in ids


def test_get_roles_registry(client):
    res = client.get("/api/v1/roles/registry")
    assert res.status_code == 200
    items = res.json()["data"]
    assert len(items) == 5
    assert all("name" in r and "shortLabel" in r for r in items)


def test_create_registry_role(client):
    res = client.post(
        "/api/v1/roles/registry",
        json={
            "id": "brand",
            "name": "苏见",
            "title": "品牌设计 · AI",
            "department": "品牌部",
            "capabilities": ["text", "image"],
            "dispatchable": True,
            "shortLabel": "品牌",
        },
    )
    assert res.status_code == 200
    entry = res.json()["data"]
    assert entry["id"] == "brand"
    assert "image" in entry["capabilities"]

    dash = client.get("/api/v1/dashboard").json()["data"]
    assert any(r["id"] == "brand" for r in dash["roles"])
    assert "brand" in dash["roleProfiles"]
    cfg = next(c for c in dash["roleConfig"] if c["roleId"] == "brand")
    assert cfg["models"]["text"]["enabled"] is True
    assert cfg["models"]["image"]["enabled"] is False


def test_create_duplicate_role_rejected(client):
    client.post(
        "/api/v1/roles/registry",
        json={"id": "brand", "name": "A", "capabilities": ["text"]},
    )
    dup = client.post(
        "/api/v1/roles/registry",
        json={"id": "brand", "name": "B", "capabilities": ["text"]},
    )
    assert dup.status_code == 409


def test_patch_role_identity(client):
    client.post(
        "/api/v1/roles/registry",
        json={"id": "brand", "name": "苏见", "capabilities": ["text"]},
    )
    res = client.patch(
        "/api/v1/roles/brand/identity",
        json={
            "name": "苏见",
            "title": "品牌设计",
            "charter": "视觉与品牌叙事",
            "department": "品牌部",
        },
    )
    assert res.status_code == 200
    role = res.json()["data"]
    assert role["charter"] == "视觉与品牌叙事"


def test_role_profile_roundtrip(client):
    client.post(
        "/api/v1/roles/registry",
        json={"id": "brand", "name": "苏见", "capabilities": ["text"]},
    )
    doc = "# Brand Profile\n\n专注视觉交付。"
    put = client.put("/api/v1/roles/brand/profile", json={"document": doc})
    assert put.status_code == 200
    get = client.get("/api/v1/roles/brand/profile")
    assert get.json()["data"]["document"] == doc


def test_role_config_models_migration(client):
    res = client.get("/api/v1/roles/config/ceo")
    assert res.status_code == 200
    cfg = res.json()["data"]
    assert "models" in cfg
    assert cfg["models"]["text"]["model"]


def test_role_config_models_update(client):
    client.post(
        "/api/v1/roles/registry",
        json={"id": "brand", "name": "苏见", "capabilities": ["text", "image"]},
    )
    res = client.put(
        "/api/v1/roles/config/brand",
        json={
            "models": {
                "text": {"model": "gpt-4o", "apiProvider": "OpenRouter"},
            },
            "monthlyBudget": 1200,
            "enabledSkills": [],
        },
    )
    assert res.status_code == 200
    cfg = res.json()["data"]
    assert cfg["models"]["text"]["model"] == "gpt-4o"
    assert cfg["monthlyBudget"] == 1200


def test_settings_summary(client):
    res = client.get("/api/v1/settings/summary")
    assert res.status_code == 200
    summary = res.json()["data"]
    assert summary["roleCount"] >= 5


def test_system_settings_patch(client):
    res = client.patch(
        "/api/v1/system/settings",
        json={"orchestration": {"ceoAutoDispatch": {"enabled": True}}},
    )
    assert res.status_code == 200
    orch = res.json()["data"]["orchestration"]
    assert orch["ceoAutoDispatch"]["enabled"] is True

    dash = client.get("/api/v1/dashboard").json()["data"]
    assert dash["systemSettings"]["orchestration"]["ceoAutoDispatch"]["enabled"] is True


def test_presentation_roles_includes_new_role(client):
    client.post(
        "/api/v1/roles/registry",
        json={"id": "brand", "name": "苏见", "capabilities": ["text"], "shortLabel": "品牌"},
    )
    dash = client.get("/api/v1/dashboard").json()["data"]
    pres = dash["presentation"]["roles"]
    assert any(r["id"] == "brand" for r in pres)
