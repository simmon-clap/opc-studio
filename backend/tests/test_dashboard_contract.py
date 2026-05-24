from tests.conftest import GOLDEN_TOP_LEVEL_KEYS


def test_dashboard_contract(client):
    response = client.get("/api/v1/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    data = body["data"]
    assert set(data.keys()) == GOLDEN_TOP_LEVEL_KEYS
    assert len(GOLDEN_TOP_LEVEL_KEYS) == 35


def test_dashboard_get_is_readonly(client):
    from app.db import session_scope
    from app.models.app_state import AppState
    from app.services.dashboard_store import DASHBOARD_KEY

    with session_scope() as session:
        row = session.get(AppState, DASHBOARD_KEY)
        assert row is not None
        before = row.updated_at
        before_json = row.value_json

    for _ in range(3):
        res = client.get("/api/v1/dashboard")
        assert res.status_code == 200

    with session_scope() as session:
        row = session.get(AppState, DASHBOARD_KEY)
        assert row is not None
        assert row.updated_at == before
        assert row.value_json == before_json
