"""Inbox deduplication tests."""

from app.pulse.modules.delivery import tick_delivery
from app.services.inbox_dedup import dedupe_active_inbox
from app.services.dashboard_store import mutate


def test_dedupe_hitl_reminder_duplicates():
    dashboard = {
        "projects": [{"id": "proj-a", "clientName": "Acme", "hitlPending": "HITL-3"}],
        "artifacts": [],
        "inbox": [
            {
                "id": "inbox-1",
                "category": "reminder",
                "title": "交付提醒 · Acme HITL 待批",
                "projectId": "proj-a",
                "status": "active",
            },
            {
                "id": "inbox-2",
                "category": "reminder",
                "title": "交付提醒 · Acme HITL 待批",
                "projectId": "proj-a",
                "status": "active",
            },
        ],
    }
    archived = dedupe_active_inbox(dashboard)
    assert archived == 1
    active = [i for i in dashboard["inbox"] if i["status"] == "active"]
    assert len(active) == 1


def test_delivery_tick_does_not_duplicate_hitl_reminder(client):
    from app.db import session_scope

    with session_scope() as session:
        with mutate(session) as dashboard:
            dashboard.setdefault("projects", []).append(
                {
                    "id": "proj-dedup",
                    "clientName": "测试客户",
                    "hitlPending": "HITL-1",
                }
            )

        tick_delivery(session)
        tick_delivery(session)

        dash = client.get("/api/v1/dashboard").json()["data"]
        reminders = [
            i
            for i in dash.get("inbox", [])
            if i.get("status") == "active"
            and i.get("projectId") == "proj-dedup"
            and i.get("category") == "reminder"
        ]
        assert len(reminders) == 1


def test_pending_tasks_show_working_status():
    from app.services.aggregates import recompute_role_live_state

    dashboard = {
        "projects": [],
        "roles": [{"id": "legal", "load": {"current": 0, "max": 2}, "projectIds": [], "extras": {}}],
        "tasks": [
            {
                "id": "t-pending",
                "roleId": "legal",
                "projectId": "proj-x",
                "title": "起草 NDA",
                "status": "pending",
            }
        ],
    }
    recompute_role_live_state(dashboard)
    legal = dashboard["roles"][0]
    assert legal["workStatus"] == "working"
    assert "队列" in legal["focus"]
