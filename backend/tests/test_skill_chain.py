"""Epic 5 — Skill chain tests."""

from __future__ import annotations

import asyncio

from app.db import session_scope
from app.orchestrator.skill_chain import execute_skill_chain
from app.services.dashboard_store import get_dashboard


def test_create_skill_chain(client):
    res = client.post(
        "/api/v1/skill-chains",
        json={
            "id": "brand_pack_v1",
            "name": "品牌交付包",
            "steps": [
                {"skillId": "general_product", "onFail": "halt"},
                {"skillId": "general_dev", "onFail": "halt"},
            ],
        },
    )
    assert res.status_code == 200
    chains = client.get("/api/v1/skill-chains").json()["data"]
    assert any(c["id"] == "brand_pack_v1" for c in chains)


def test_chain_route_first_step(client):
    client.post(
        "/api/v1/skill-chains",
        json={
            "id": "chain_test",
            "name": "Test",
            "steps": [{"skillId": "nda_review_v2", "onFail": "halt"}],
        },
    )
    from app.presentation.skills import route_skill

    dash = client.get("/api/v1/dashboard").json()["data"]
    skill = route_skill(
        dash,
        role_id="legal",
        task_kind="legal.nda",
        skill_chain_id="chain_test",
    )
    assert skill is not None
    assert skill["id"] == "nda_review_v2"


def test_execute_skill_chain_stub(client):
    client.post(
        "/api/v1/skill-chains",
        json={
            "id": "exec_chain",
            "name": "Exec",
            "steps": [{"skillId": "general_product", "onFail": "halt"}],
        },
    )
    with session_scope() as session:
        dashboard = get_dashboard(session)
        task = {
            "id": "task-chain-1",
            "roleId": "product",
            "title": "链式 PRD",
            "projectId": "proj-acme",
        }
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                execute_skill_chain(
                    session,
                    dashboard,
                    chain_id="exec_chain",
                    role_id="product",
                    project_id="proj-acme",
                    base_task=task,
                )
            )
        finally:
            loop.close()
    assert result.status == "completed"
    assert len(result.steps) == 1
