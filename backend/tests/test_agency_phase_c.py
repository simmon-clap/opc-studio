"""Phase C — proposal dispatch, auto-dispatch, deliberate."""

from app.agency.auto_dispatch import apply_auto_dispatch, should_auto_dispatch
from app.agency.deliberate import deliberate_merge_proposals
from app.agency.proposal_actions import execute_proposal_dispatch
from app.services.dashboard_store import mutate


def _proposal_item(**overrides):
    item = {
        "id": "inbox-prop-1",
        "category": "proposal",
        "from": "product",
        "to": "ceo",
        "title": "建议：测试客户 可撰写 PRD",
        "preview": "项目尚无 PRD 产出",
        "projectId": "proj-test",
        "status": "active",
        "read": False,
        "proposal": {
            "signalType": "artifact.missing",
            "fingerprint": "artifact.missing:prd:proj-test",
            "priority": "medium",
            "riskLevel": "low",
            "suggestedAction": "dispatch",
            "suggestedRole": "product",
            "suggestedTitle": "测试客户 · 需求 PRD 初稿",
        },
    }
    item.update(overrides)
    return item


def test_proposal_manual_dispatch_on_approve(client):
    from app.db import session_scope

    with session_scope() as session:
        with mutate(session) as dashboard:
            dashboard["inbox"] = [_proposal_item()]
            dashboard.setdefault("meta", {})["runtimeSettings"] = {"agency": {"enabled": True}}

    resp = client.post("/api/v1/inbox/inbox-prop-1/resolve", json={"action": "approve"})
    assert resp.status_code == 200

    dash = client.get("/api/v1/dashboard").json()["data"]
    tasks = [t for t in dash.get("tasks", []) if t.get("roleId") == "product"]
    assert tasks
    assert tasks[0]["status"] in {"pending", "running", "done"}
    assert "PRD" in tasks[0].get("title", "")
    inbox = next(i for i in dash["inbox"] if i["id"] == "inbox-prop-1")
    assert inbox["status"] == "done"


def test_auto_dispatch_when_enabled(client):
    from app.db import session_scope

    with session_scope() as session:
        with mutate(session) as dashboard:
            dashboard["projects"] = [
                {"id": "proj-test", "clientName": "测试", "pipelineColumn": "active"}
            ]
            dashboard["artifacts"] = [
                {
                    "id": "art-1",
                    "projectId": "proj-test",
                    "status": "approved",
                    "ceoReviewScore": 90,
                    "quality": {"score": 90},
                }
            ]
            dashboard["inbox"] = [_proposal_item()]
            dashboard.setdefault("meta", {})["runtimeSettings"] = {
                "agency": {"enabled": True},
                "ceoAutoDispatch": {
                    "enabled": True,
                    "minDeliveryScore": 80,
                    "maxRiskLevel": "low",
                    "cooldownMin": 15,
                },
            }
            result = apply_auto_dispatch(dashboard)

        assert result["dispatched"] == 1
        dash = client.get("/api/v1/dashboard").json()["data"]
        assert any(t.get("roleId") == "product" for t in dash.get("tasks", []))
        inbox = next(i for i in dash["inbox"] if i["id"] == "inbox-prop-1")
        assert inbox.get("resolution") == "auto_approved"


def test_auto_dispatch_blocked_when_score_low(client):
    from app.db import session_scope

    with session_scope() as session:
        with mutate(session) as dashboard:
            dashboard["artifacts"] = [
                {"id": "art-1", "projectId": "proj-test", "status": "approved", "ceoReviewScore": 50}
            ]
            dashboard["inbox"] = [_proposal_item()]
            dashboard.setdefault("meta", {})["runtimeSettings"] = {
                "ceoAutoDispatch": {"enabled": True, "minDeliveryScore": 80, "maxRiskLevel": "low"},
            }
            item = dashboard["inbox"][0]
            assert not should_auto_dispatch(dashboard, item)


def test_deliberate_merges_same_project_proposals():
    dashboard = {
        "inbox": [
            _proposal_item(id="inbox-a", preview="A"),
            _proposal_item(
                id="inbox-b",
                title="建议 B",
                preview="B",
                proposal={
                    "signalType": "pipeline.process",
                    "fingerprint": "pipeline.process:proj-test:x",
                    "priority": "low",
                    "riskLevel": "low",
                    "suggestedAction": "review",
                },
            ),
        ]
    }
    result = deliberate_merge_proposals(dashboard)
    assert result["mergedGroups"] == 1
    assert result["archived"] == 1
    active = [i for i in dashboard["inbox"] if i.get("status") == "active"]
    assert len(active) == 1
    assert active[0].get("proposal", {}).get("mergedCount") == 2


def test_execute_proposal_dispatch_creates_pending_task():
    dashboard = {"projects": [{"id": "proj-test"}], "tasks": [], "inbox": []}
    item = _proposal_item()
    task = execute_proposal_dispatch(dashboard, item)
    assert task
    assert task["status"] == "pending"
    assert task["roleId"] == "product"
