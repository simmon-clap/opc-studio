def test_role_config_masks(client):
    put = client.put(
        "/api/v1/roles/config/ceo",
        json={
            "model": "gpt-4o",
            "apiProvider": "OpenRouter",
            "apiBaseUrl": "https://openrouter.ai/api/v1",
            "apiKey": "sk-test-secret-key-abc",
            "monthlyBudget": 900,
        },
    )
    assert put.status_code == 200
    updated = put.json()["data"]
    assert updated["apiKey"]["masked"].endswith("abc")
    assert "sk-test" not in updated["apiKey"]["masked"]

    configs = client.get("/api/v1/roles/config").json()["data"]
    ceo = next(c for c in configs if c["roleId"] == "ceo")
    assert ceo["apiKey"]["masked"].endswith("abc")
    assert ceo["monthlyBudget"] == 900
