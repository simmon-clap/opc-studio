"""Project progress derivation tests."""

from app.presentation.project_progress import (
    compute_project_progress,
    parse_stage_index,
    recompute_projects_progress,
)


def test_parse_stage_index():
    assert parse_stage_index("阶段4 · 开发交付") == 4
    assert parse_stage_index("阶段1 · 线索") == 1


def test_progress_uses_tasks_and_artifacts():
    dashboard = {
        "projects": [
            {
                "id": "proj-a",
                "stage": "阶段4 · 开发交付",
                "pipelineColumn": "active",
                "hitlPending": "HITL-3",
            }
        ],
        "artifacts": [
            {"id": "a1", "projectId": "proj-a", "kind": "demo", "status": "approved"},
            {"id": "a2", "projectId": "proj-a", "kind": "prd", "status": "approved"},
        ],
        "tasks": [
            {
                "id": "t1",
                "projectId": "proj-a",
                "status": "running",
                "progress": 95,
                "progressNote": "自测 4/5",
                "stage": "阶段4 · 开发交付",
                "roleId": "dev",
            }
        ],
        "closure": {},
    }
    detail = compute_project_progress(dashboard, dashboard["projects"][0])
    assert detail["stageIndex"] == 4
    assert detail["currentStageGroup"] == "engineering"
    assert detail["executionProgress"] == 95
    assert detail["progress"] >= 60


def test_recompute_projects_progress_mutates_dashboard():
    dashboard = {
        "projects": [{"id": "p", "stage": "阶段2 · 评估立项", "pipelineColumn": "clarify"}],
        "artifacts": [],
        "tasks": [],
        "closure": {},
    }
    recompute_projects_progress(dashboard)
    assert dashboard["projects"][0]["progressDetail"]["stageIndex"] == 2
