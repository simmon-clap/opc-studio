"""Pulse runtime tests."""

import asyncio

from app.orchestrator import dispatcher
from app.pulse.coordinator import drain_pending_queue
from app.services.dashboard_store import mutate


def test_runtime_settings_defaults(client):
    resp = client.get("/api/v1/runtime/settings")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["pulse"]["executionIntervalSec"] == 5
    assert data["ceoAutoDispatch"]["enabled"] is False


def test_runtime_settings_patch(client):
    resp = client.patch(
        "/api/v1/runtime/settings",
        json={
            "pulse": {"runningStaleMin": 45},
            "ceoAutoDispatch": {"enabled": True, "minDeliveryScore": 85},
        },
    )
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["pulse"]["runningStaleMin"] == 45
    assert body["ceoAutoDispatch"]["enabled"] is True
    assert body["ceoAutoDispatch"]["minDeliveryScore"] == 85


def test_dispatch_creates_pending(client):
    from app.db import session_scope

    with session_scope() as session:
        with mutate(session) as dashboard:
            task = dispatcher.dispatch_task(
                dashboard,
                role_id="legal",
                project_id="proj-beta",
                title="测试 pending 任务",
                deliverable_kind="nda",
            )
            task_id = task["id"]
    dash = client.get("/api/v1/dashboard").json()["data"]
    saved = next(t for t in dash["tasks"] if t["id"] == task_id)
    assert saved["status"] == "pending"


def test_drain_executes_pending(client):
    from app.db import session_scope

    with session_scope() as session:
        with mutate(session) as dashboard:
            dashboard["tasks"] = []
            task = dispatcher.dispatch_task(
                dashboard,
                role_id="legal",
                project_id="proj-beta",
                title="Drain 测试 NDA",
                deliverable_kind="nda",
                priority="urgent",
            )
            task_id = task["id"]

    async def run():
        from app.db import session_scope

        with session_scope() as session:
            return await drain_pending_queue(session, max_tasks=3)

    ran = asyncio.run(run())
    assert ran >= 1
    dash = client.get("/api/v1/dashboard").json()["data"]
    saved = next(t for t in dash["tasks"] if t["id"] == task_id)
    assert saved["status"] == "done"


def test_pulse_status_endpoint(client):
    resp = client.get("/api/v1/pulse/status")
    assert resp.status_code == 200
    assert "enabled" in resp.json()["data"]
