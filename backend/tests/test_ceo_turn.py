"""CEO turn rule fallback tests."""

import asyncio

from app.orchestrator.ceo_turn import apply_turn_side_effects, run_ceo_turn
from app.orchestrator.directives import detect_context_directives


def test_rule_turn_dispatches_nda_followup():
    dashboard = {
        "clients": [{"name": "华为", "projectIds": ["lead-华为"]}],
        "projects": [{"id": "lead-华为", "clientName": "华为"}],
        "roles": [{"id": "legal", "name": "法务"}],
        "ceoThread": [
            {"direction": "founder_to_ceo", "text": "华为 NDA 双向"},
        ],
        "commitments": [],
        "projectBriefs": {},
    }
    text = "NDA 没有更新，重新生成专业的双向 NDA"

    async def main():
        from app.db import session_scope, init_db

        init_db()
        with session_scope() as session:
            turn = await run_ceo_turn(session, dashboard, text, "lead-华为")
            apply_turn_side_effects(dashboard, turn, source="test")
            return turn

    turn = asyncio.run(main())
    assert turn.dispatch_plan.should_dispatch
    assert any(d.role_id == "legal" for d in turn.dispatch_plan.directives)


def test_detect_context_still_works():
    dashboard = {
        "ceoThread": [{"direction": "founder_to_ceo", "text": "华为 NDA"}],
    }
    dirs = detect_context_directives("NDA 没更新", dashboard, "lead-华为")
    assert dirs and dirs[0].kind == "nda"


def test_status_query_summarizes_tasks():
    dashboard = {
        "roles": [{"id": "legal", "name": "唐律"}],
        "projects": [{"id": "p1", "clientName": "华为"}],
        "tasks": [
            {
                "id": "t1",
                "roleId": "legal",
                "projectId": "p1",
                "title": "华为 · NDA",
                "status": "running",
            }
        ],
        "commitments": [],
        "projectBriefs": {},
    }

    async def main():
        from app.db import session_scope, init_db

        init_db()
        with session_scope() as session:
            return await run_ceo_turn(
                session, dashboard, "我们现在有哪些任务在进行？", "p1"
            )

    turn = asyncio.run(main())
    assert not turn.dispatch_plan.should_dispatch
    assert "华为" in turn.reply or "NDA" in turn.reply
    assert "有明确派活指令" not in turn.reply
