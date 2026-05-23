"""Dispatch planner tests."""

from app.orchestrator.dispatch_planner import DispatchPlan, _normalize_plan, _plan_from_rules


def test_normalize_multi_role_directives():
    raw = {
        "should_dispatch": True,
        "mode": "directives",
        "reason": "法务写 NDA，运营登记",
        "tasks": [
            {"role": "legal", "title": "起草华为 NDA", "kind": "nda"},
            {"role": "ops", "title": "登记华为线索", "kind": "ops_lead"},
        ],
    }
    plan = _normalize_plan(raw)
    assert plan.should_dispatch
    assert plan.mode == "directives"
    assert len(plan.directives) == 2
    assert plan.directives[0].role_id == "legal"


def test_rules_fallback_nda():
    text = "法务就华为这个项目把 NDA 写出来"
    plan = _plan_from_rules(text)
    assert plan.should_dispatch
    assert plan.mode == "directives"
    assert any(d.role_id == "legal" for d in plan.directives)


def test_rules_chat_only_no_dispatch():
    plan = _plan_from_rules("你觉得 Beta 这个项目靠谱吗")
    assert not plan.should_dispatch


def test_plan_roundtrip():
    plan = DispatchPlan(
        should_dispatch=True,
        mode="directives",
        reason="test",
        directives=[],
    )
    restored = DispatchPlan.from_dict(plan.to_dict())
    assert restored.should_dispatch == plan.should_dispatch
