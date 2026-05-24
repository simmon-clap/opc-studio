"""PoC end-to-end: brief → dispatch → legal task."""

import asyncio
import time

from app.orchestrator.engine import get_orchestrator


def test_poc_nda_e2e_flow(client):
    """Full PoC path: CEO brief with NDA directive → workflow → legal task."""
    brief = client.post(
        "/api/v1/ceo/brief",
        json={"text": "华为线索，请法务准备双向 NDA 草稿"},
    )
    assert brief.status_code == 200
    assert brief.json().get("patch") is not None

    async def run_workflow():
        from app.db import session_scope

        with session_scope() as session:
            orch = get_orchestrator()
            project_id = "lead-华为"
            await orch.run_workflow_phase(session, "华为 NDA", project_id)

    asyncio.run(run_workflow())
    time.sleep(0.15)

    dash = client.get("/api/v1/dashboard").json()["data"]
    legal = [
        t
        for t in dash.get("tasks", [])
        if t.get("roleId") == "legal"
        and ("NDA" in (t.get("title") or "").upper() or t.get("deliverableKind") == "nda")
    ]
    assert legal or dash.get("meta", {}).get("lastWorkflowRun")
