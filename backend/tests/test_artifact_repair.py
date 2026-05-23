"""Artifact repair tests."""

from app.services.artifact_repair import repair_missing_artifacts


def test_repair_creates_nda_for_done_legal_task():
    dashboard = {
        "projects": [
            {
                "id": "lead-华为",
                "clientName": "华为（线索）",
                "assignees": ["ceo", "product"],
            }
        ],
        "artifacts": [
            {
                "id": "art-product-1",
                "projectId": "lead-华为",
                "title": "PRD 草稿",
                "roleId": "product",
                "content": "# PRD",
            }
        ],
        "tasks": [
            {
                "id": "task-legal-1",
                "roleId": "legal",
                "projectId": "lead-华为",
                "title": "华为 · 起草 NDA",
                "status": "done",
                "completedAt": "2026-05-21T17:18:00+08:00",
            }
        ],
    }
    repaired = repair_missing_artifacts(dashboard)
    assert repaired == 1
    nda = next(a for a in dashboard["artifacts"] if "NDA" in a["title"])
    assert nda["projectId"] == "lead-华为"
    assert nda["roleId"] == "legal"
    assert "保密" in nda["content"] or "保密信息" in nda["content"]
    assert "legal" in dashboard["projects"][0]["assignees"]
