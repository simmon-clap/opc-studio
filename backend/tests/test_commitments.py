"""Commitment service tests."""

from app.services.commitments import (
    apply_commitment_actions,
    close_commitment,
    list_commitments,
    open_commitment,
    overdue_commitments,
)


def test_open_and_close_commitment():
    dashboard: dict = {"commitments": []}
    item = open_commitment(
        dashboard,
        project_id="lead-华为",
        what="法务重拟 NDA",
        owner_role="legal",
        due_at="2020-01-01T00:00:00+08:00",
    )
    assert item["status"] == "open"
    assert len(list_commitments(dashboard, status="open")) == 1
    close_commitment(dashboard, item["id"])
    assert list_commitments(dashboard, status="open") == []


def test_overdue_detection():
    dashboard = {
        "commitments": [
            {
                "id": "cmt-1",
                "status": "open",
                "dueAt": "2020-01-01T00:00:00+08:00",
                "projectId": "p1",
            }
        ]
    }
    assert len(overdue_commitments(dashboard)) == 1


def test_apply_commitment_actions():
    dashboard: dict = {"commitments": []}
    created = apply_commitment_actions(
        dashboard,
        [{"action": "open", "what": "写 PRD", "ownerRole": "product"}],
        project_id="proj-beta",
    )
    assert len(created) == 1
    assert created[0]["ownerRole"] == "product"
