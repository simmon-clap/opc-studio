from tests.conftest import GOLDEN_TOP_LEVEL_KEYS


def test_dashboard_contract(client):
    response = client.get("/api/v1/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    data = body["data"]
    assert set(data.keys()) == GOLDEN_TOP_LEVEL_KEYS
    assert len(GOLDEN_TOP_LEVEL_KEYS) == 28
