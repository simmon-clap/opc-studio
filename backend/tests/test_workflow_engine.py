"""Workflow engine next-steps tests."""

from app.orchestrator.workflow_engine import get_focus_and_others, get_next_steps


def test_open_questions_surface_as_steps():
    dashboard = {
        "projects": [{"id": "lead-coke", "clientName": "可口可乐", "pipelineColumn": "lead"}],
        "projectBriefs": {
            "lead-coke": {"openQuestions": ["数据接入方式？"]},
        },
        "commitments": [],
        "artifacts": [],
        "tasks": [],
        "hitlQueue": [],
    }
    steps = get_next_steps(dashboard, "lead-coke")
    assert any(s["type"] == "question" for s in steps)


def test_focus_and_others_split():
    dashboard = {
        "projects": [{"id": "p1", "clientName": "X", "pipelineColumn": "lead"}],
        "projectBriefs": {"p1": {"openQuestions": ["Q1", "Q2"]}},
        "commitments": [],
        "artifacts": [],
        "tasks": [],
        "hitlQueue": [],
    }
    focus, others = get_focus_and_others(dashboard, "p1")
    assert focus is not None
    assert len(others) >= 1
