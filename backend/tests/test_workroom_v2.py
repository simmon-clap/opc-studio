"""Workroom v2 presenter and artifact action tests."""

from app.orchestrator.workflow_engine import get_focus_and_others
from app.presentation.artifact_actions import (
    artifact_actions,
    artifact_export_formats,
    artifact_status_dot,
)
from app.presentation.workroom import build_workroom_payload


def test_artifact_status_dot_waiting_on_review():
    assert artifact_status_dot({"status": "review"}) == "waiting"


def test_artifact_actions_hitl_approve_reject():
    actions = artifact_actions({"status": "review", "hitlId": "h1", "kind": "nda"})
    ids = [a["id"] for a in actions]
    assert ids == ["approve", "reject"]


def test_artifact_actions_draft_with_pending():
    actions = artifact_actions({"status": "draft", "pendingFields": 2, "kind": "nda"})
    ids = [a["id"] for a in actions]
    assert "edit" in ids
    assert "submit_review" in ids


def test_artifact_export_formats_includes_zip_when_files():
    formats = artifact_export_formats({"files": [{"path": "a.py"}]})
    assert any(f["id"] == "zip" for f in formats)


def test_focus_prioritizes_hitl():
    dashboard = {
        "projects": [
            {
                "id": "proj-a",
                "clientName": "Acme",
                "hitlPending": "HITL-3",
                "stage": "阶段4",
            }
        ],
        "hitlQueue": [
            {
                "id": "hitl-3",
                "type": "HITL-3",
                "projectId": "proj-a",
                "title": "审交付物",
            }
        ],
        "artifacts": [
            {
                "id": "art-1",
                "projectId": "proj-a",
                "status": "review",
                "hitlId": "hitl-3",
                "title": "交付包",
            }
        ],
        "projectBriefs": {"proj-a": {"openQuestions": ["范围？"]}},
        "tasks": [],
        "commitments": [],
    }
    focus, others = get_focus_and_others(dashboard, "proj-a")
    assert focus is not None
    assert focus["type"] == "hitl"


def test_build_workroom_payload_groups_and_export_menu():
    dashboard = {
        "projects": [
            {
                "id": "proj-a",
                "clientName": "Acme",
                "stage": "阶段3",
                "progress": 55,
                "hitlPending": None,
            }
        ],
        "artifacts": [
            {
                "id": "art-prd",
                "projectId": "proj-a",
                "kind": "prd",
                "title": "PRD",
                "status": "draft",
                "version": "0.1",
            }
        ],
        "projectBriefs": {"proj-a": {"openQuestions": ["预算？"]}},
        "closure": {},
        "tasks": [],
        "commitments": [],
    }
    payload = build_workroom_payload(dashboard, "proj-a")
    assert payload["header"]["clientName"] == "Acme"
    assert payload["exportMenu"]
    assert payload["header"]["priority"]
    legal = next((g for g in payload["groups"] if g["id"] == "legal"), None)
    evaluate = next(g for g in payload["groups"] if g["id"] == "evaluate")
    assert any(f["type"] == "brief" for f in evaluate["fold"])
    assert legal and legal["artifacts"][0]["actions"]
