"""Workflow engine next-steps tests."""

from app.orchestrator.workflow_engine import get_next_steps


def test_open_questions_surface_as_steps():
    dashboard = {
        "projects": [{"id": "lead-coke", "clientName": "可口可乐", "pipelineColumn": "lead"}],
        "projectBriefs": {
            "lead-coke": {"openQuestions": ["数据接入方式？"]},
        },
        "commitments": [],
        "artifacts": [],
    }
    steps = get_next_steps(dashboard, "lead-coke")
    assert any(s["type"] == "question" for s in steps)
