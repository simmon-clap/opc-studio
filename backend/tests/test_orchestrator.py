"""Orchestrator integration tests."""

import asyncio
import time

from app.orchestrator.engine import get_orchestrator


def test_ceo_brief_casual_no_deliberation(client):
    asyncio.run(
        get_orchestrator().on_event("ceo.brief", {"text": "halo", "projectId": "proj-beta"})
    )
    dash = client.get("/api/v1/dashboard").json()["data"]
    thread = dash.get("ceoThread", [])
    ceo_msgs = [m for m in thread if m.get("direction") == "ceo_to_founder"]
    assert ceo_msgs
    last = ceo_msgs[-1]["text"]
    assert "立项" in last or "随便聊" in last
    assert "Decision Memo" not in last


def test_ceo_brief_vague_chat_only(client):
    asyncio.run(
        get_orchestrator().on_event("ceo.brief", {"text": "做个系统", "projectId": "proj-beta"})
    )
    dash = client.get("/api/v1/dashboard").json()["data"]
    assert not any("Decision Memo" in a.get("title", "") for a in dash.get("artifacts", []))


def test_ceo_brief_vague_with_command_opens_deliberation(client):
    async def run_workflow():
        from app.db import session_scope

        with session_scope() as session:
            await get_orchestrator().run_workflow_phase(
                session, "做个系统，安排立项", "proj-beta"
            )

    asyncio.run(run_workflow())
    time.sleep(0.1)
    dash = client.get("/api/v1/dashboard").json()["data"]
    assert any("Decision Memo" in a.get("title", "") for a in dash.get("artifacts", []))
    delib = client.get("/api/v1/projects/proj-beta/deliberation").json()["data"]
    assert delib is not None
    assert delib["status"] == "closed"
    assert len(delib.get("turns", [])) >= 2


def test_hitl_approve_dispatches_task(client):
    hitl_id = "hitl-3-acme"
    resp = client.post(f"/api/v1/hitl/{hitl_id}/approve")
    assert resp.status_code == 200
    time.sleep(0.2)
    dash = client.get("/api/v1/dashboard").json()["data"]
    ops_tasks = [
        t
        for t in dash.get("tasks", [])
        if t.get("roleId") == "ops" and "结项" in t.get("title", "")
    ]
    assert ops_tasks
