"""LLM test endpoint tests."""

from unittest.mock import AsyncMock, patch

from app.services.llm_client import LlmResponse


def test_role_config_test_endpoint(client):
    # Save fake key first
    client.put(
        "/api/v1/roles/config/ceo",
        json={
            "model": "gpt-4o-mini",
            "apiProvider": "OpenAI",
            "apiBaseUrl": "https://api.example.com/v1",
            "apiKey": "sk-test-key",
        },
    )
    mock_resp = LlmResponse(
        content="OPC_OK",
        model="gpt-4o-mini",
        input_tokens=5,
        output_tokens=2,
        raw={},
    )
    with patch(
        "app.api.roles.test_connection",
        new=AsyncMock(return_value=mock_resp),
    ):
        r = client.post("/api/v1/roles/config/ceo/test")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["data"]["sample"] == "OPC_OK"
