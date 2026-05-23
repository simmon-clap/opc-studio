"""Editable per-role system prompt."""

from app.runners.prompts import default_role_prompt, system_prompt


def test_custom_role_prompt_overrides_default():
    custom = "你是首席法务，只输出合同级 NDA，禁止 bullet。"
    assert system_prompt("legal", "林法务", "合同审查", custom) == custom


def test_default_role_prompt_uses_charter():
    doc = default_role_prompt("product", "周产品", "PRD 与验收")
    assert "周产品" in doc
    assert "PRD 与验收" in doc
    assert system_prompt("product", "周产品", "PRD 与验收") == doc


def test_role_prompt_api_roundtrip(client):
    custom = "你是测试 CEO，回复不超过 3 句。"
    resp = client.put("/api/v1/roles/config/ceo", json={"rolePrompt": custom})
    assert resp.status_code == 200
    assert resp.json()["data"]["rolePrompt"] == custom

    configs = client.get("/api/v1/roles/config").json()["data"]
    ceo = next(c for c in configs if c["roleId"] == "ceo")
    assert ceo["rolePrompt"] == custom
