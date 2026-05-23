"""Directive dispatch integration test."""

import asyncio

from app.orchestrator.engine import get_orchestrator


def test_nda_directive_dispatches_legal(client):
    text = "法务开始就 NDA 写一下，写好了发我 NDA"

    async def run_workflow():
        from app.db import session_scope

        with session_scope() as session:
            await get_orchestrator().run_workflow_phase(session, text, "proj-beta")

    asyncio.run(run_workflow())
    dash = client.get("/api/v1/dashboard").json()["data"]
    legal_tasks = [
        t
        for t in dash.get("tasks", [])
        if t.get("roleId") == "legal" and "NDA" in t.get("title", "")
    ]
    assert legal_tasks
    assert legal_tasks[0]["status"] == "done"
    nda_arts = [
        a
        for a in dash.get("artifacts", [])
        if a.get("roleId") == "legal" and "NDA" in a.get("title", "")
    ]
    assert nda_arts
    thread = dash.get("ceoThread", [])
    assert any("已派活" in m.get("text", "") for m in thread if m.get("type") == "decision")
