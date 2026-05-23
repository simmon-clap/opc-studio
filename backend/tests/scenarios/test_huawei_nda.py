"""Huawei NDA vertical scenario."""

import asyncio
import time

from app.orchestrator.engine import get_orchestrator


def test_huawei_nda_directive_flow(client):
    text = "NDA 没有更新，重新生成一份专业的双向 NDA"

    async def run():
        from app.db import session_scope

        with session_scope() as session:
            project_id, sched = await get_orchestrator().run_ceo_turn_phase(
                session, text, "lead-华为"
            )
            assert sched
            await get_orchestrator().run_workflow_phase(session, text, project_id)

    asyncio.run(run())
    time.sleep(0.1)
    dash = client.get("/api/v1/dashboard").json()["data"]

    briefs = dash.get("projectBriefs", {})
    assert any(b.get("ndaType") == "mutual" for b in briefs.values()) or briefs
    open_cmts = [c for c in dash.get("commitments", []) if c.get("status") == "open"]
    assert open_cmts or any(
        t.get("roleId") == "legal" for t in dash.get("tasks", []) if "华为" in t.get("title", "")
    )
    legal_tasks = [
        t
        for t in dash.get("tasks", [])
        if t.get("roleId") == "legal"
        and (t.get("deliverableKind") == "nda" or "NDA" in t.get("title", ""))
    ]
    assert legal_tasks
    assert dash["meta"].get("lastWorkflowRun")


def test_commitments_api(client):
    resp = client.get("/api/v1/commitments")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_founder_profile_api(client):
    resp = client.get("/api/v1/founder/profile")
    assert resp.status_code == 200
    assert "communication" in resp.json()["data"]
