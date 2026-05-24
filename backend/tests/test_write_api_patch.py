"""Write API DashboardPatch coverage."""

from app.db import session_scope
from app.services.dashboard_store import mutate


def test_inbox_patch_returns_dashboard_slice(client):
    dash = client.get("/api/v1/dashboard").json()["data"]
    item = next((i for i in dash.get("inbox", []) if i.get("status") == "active"), None)
    if not item:
        with session_scope() as session:
            with mutate(session) as d:
                d.setdefault("inbox", []).insert(
                    0,
                    {
                        "id": "inbox-patch-test",
                        "category": "reminder",
                        "title": "patch test",
                        "status": "active",
                        "read": False,
                    },
                )
        item = {"id": "inbox-patch-test"}

    res = client.patch(f"/api/v1/inbox/{item['id']}", json={"read": True})
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert "patch" in body
    assert "inbox" in body["patch"]


def test_project_patch_returns_dashboard_slice(client):
    dash = client.get("/api/v1/dashboard").json()["data"]
    project = (dash.get("projects") or [{}])[0]
    pid = project.get("id")
    if not pid:
        return
    res = client.patch(f"/api/v1/projects/{pid}", json={"summary": "patch test summary"})
    assert res.status_code == 200
    body = res.json()
    assert "patch" in body
    assert "projects" in body["patch"] or "pulse" in body["patch"]


def test_hitl_reject_returns_patch(client):
    dash = client.get("/api/v1/dashboard").json()["data"]
    hitl = next((h for h in dash.get("hitlQueue", []) if h.get("status") == "pending"), None)
    if not hitl:
        return
    res = client.post(f"/api/v1/hitl/{hitl['id']}/reject", json={"note": "test reject"})
    assert res.status_code == 200
    assert "patch" in res.json()
