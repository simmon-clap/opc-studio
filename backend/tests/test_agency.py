"""Agency observe and proposal bus tests."""

import asyncio

from app.agency.runner import tick_agency
from app.services.dashboard_store import mutate


def _minimal_dashboard(**overrides):
    base = {
        "meta": {"runtimeSettings": {"agency": {"enabled": True}}},
        "projects": [
            {
                "id": "proj-test",
                "clientName": "测试客户",
                "pipelineColumn": "lead",
                "assignees": [],
            }
        ],
        "roles": [{"id": "product"}, {"id": "legal"}, {"id": "ceo"}],
        "tasks": [],
        "artifacts": [],
        "inbox": [],
        "projectBriefs": {},
        "commitments": [],
        "ceoThread": [],
    }
    base.update(overrides)
    return base


def _run_agency(session, **kwargs):
    return asyncio.run(tick_agency(session, **kwargs))


def test_agency_product_proposal_for_missing_prd(client):
    from app.db import session_scope

    with session_scope() as session:
        with mutate(session) as dashboard:
            dashboard.clear()
            dashboard.update(_minimal_dashboard())

        _run_agency(session, role_id="product")

        dash = client.get("/api/v1/dashboard").json()["data"]
        proposals = [
            i
            for i in dash.get("inbox", [])
            if i.get("category") == "proposal" and i.get("from") == "product"
        ]
        assert proposals
        assert proposals[0].get("proposal", {}).get("signalType") == "artifact.missing"


def test_agency_proposal_dedup(client):
    from app.db import session_scope

    with session_scope() as session:
        with mutate(session) as dashboard:
            dashboard.clear()
            dashboard.update(_minimal_dashboard())

        first = _run_agency(session, role_id="product")
        second = _run_agency(session, role_id="product")
        assert first.get("created", 0) >= 1
        assert second.get("created", 0) == 0

        dash = client.get("/api/v1/dashboard").json()["data"]
        fps = [
            i.get("proposal", {}).get("fingerprint")
            for i in dash.get("inbox", [])
            if i.get("category") == "proposal"
        ]
        assert len(fps) == len(set(f for f in fps if f))


def test_agency_paused_during_orchestration(client):
    from app.db import session_scope

    with session_scope() as session:
        with mutate(session) as dashboard:
            dashboard.clear()
            dashboard.update(
                _minimal_dashboard(
                    meta={
                        "orchestrationActive": True,
                        "runtimeSettings": {"agency": {"enabled": True}},
                    }
                )
            )

        result = _run_agency(session, role_id="ceo")
        assert result.get("action") == "paused"
