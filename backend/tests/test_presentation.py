"""Presentation layer tests."""

from app.presentation.blocks import message_content, paragraph, task_row
from app.presentation.derived import recompute_presentation
from app.presentation.schema import PRESENTATION_VERSION
from app.services.ops_status import summarize_active_work_content


def test_message_content_envelope():
    content = message_content([paragraph("你好"), task_row(role="唐律", title="NDA", status="执行中")])
    assert content["version"] == PRESENTATION_VERSION
    assert len(content["blocks"]) == 2
    assert "NDA" in content["text"]


def test_recompute_presentation_sets_root_and_alias():
    dashboard = {
        "roles": [{"id": "legal", "name": "唐律", "workStatus": "working"}],
        "projects": [],
        "tasks": [],
        "dispatchFeed": [],
        "meta": {},
    }
    recompute_presentation(dashboard)
    assert dashboard["presentation"]["version"] == PRESENTATION_VERSION
    assert dashboard["presentation"]["roles"]
    assert dashboard["presentation"]["overview"]["version"] == PRESENTATION_VERSION
    assert dashboard["overviewLive"] is dashboard["presentation"]["overview"]


def test_status_query_content_has_task_rows():
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
        "meta": {},
    }
    content = summarize_active_work_content(dashboard)
    assert any(b.get("type") == "task_row" for b in content["blocks"])
    assert any(b.get("type") == "heading" for b in content["blocks"])
