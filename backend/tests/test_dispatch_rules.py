"""Dispatch rules import tests."""

from app.orchestrator.dispatch_rules import plan_from_rules, plan_should_dispatch


def test_plan_should_dispatch_nda():
    assert plan_should_dispatch("法务写 NDA")


def test_import_engine_no_cycle():
    from app.orchestrator import engine  # noqa: F401

    assert engine.get_orchestrator() is not None
