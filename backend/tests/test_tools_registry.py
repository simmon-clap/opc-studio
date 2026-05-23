"""Epic 2 — Tool Registry tests."""

from __future__ import annotations

import json

import pytest

from app.runners.base import RunContext
from app.tools.registry import (
    ToolExecutionContext,
    bootstrap_tools,
    execute_tool,
    list_tools,
    resolve_allowed_tools,
)


@pytest.fixture(autouse=True)
def _tools():
    bootstrap_tools()
    yield


def test_tools_registered():
    ids = {t.id for t in list_tools()}
    assert "read_project_brief" in ids
    assert "write_artifact_file" in ids
    assert "propose_skill_install" in ids


def test_resolve_allowed_tools_dev(client):
    dash = client.get("/api/v1/dashboard").json()["data"]
    allowed = resolve_allowed_tools(dash, "dev")
    assert "write_artifact_file" in allowed


def test_tool_not_allowed_for_role(client):
    dash = client.get("/api/v1/dashboard").json()["data"]
    ctx = ToolExecutionContext(
        dashboard=dash,
        role_id="ops",
        project_id="proj-acme",
        task={"id": "t1", "roleId": "ops"},
    )
    import asyncio

    loop = asyncio.new_event_loop()
    try:
        rec = loop.run_until_complete(
            execute_tool(
                "dispatch_task",
                {"roleId": "dev", "projectId": "p", "title": "x"},
                ctx,
                allowed_tools=["update_pipeline"],
            )
        )
    finally:
        loop.close()
    assert rec.error and "TOOL_NOT_ALLOWED" in rec.error


def test_write_artifact_tool(client):
    dash = client.get("/api/v1/dashboard").json()["data"]
    ctx = ToolExecutionContext(
        dashboard=dash,
        role_id="dev",
        project_id="proj-acme",
        task={"id": "t1", "roleId": "dev"},
    )
    import asyncio

    loop = asyncio.new_event_loop()
    try:
        rec = loop.run_until_complete(
            execute_tool(
                "write_artifact_file",
                {"projectId": "proj-acme", "title": "Test", "content": "# Hi"},
                ctx,
                allowed_tools=resolve_allowed_tools(dash, "dev"),
            )
        )
    finally:
        loop.close()
    assert rec.result and rec.result.get("artifactId")
    assert any(a.get("title") == "Test" for a in dash.get("artifacts", []))


def test_tools_api(client):
    res = client.get("/api/v1/tools")
    assert res.status_code == 200
    assert len(res.json()["data"]) >= 7


def test_effective_tools_api(client):
    res = client.get("/api/v1/tools/effective/dev")
    assert res.status_code == 200
    assert "write_artifact_file" in res.json()["data"]["allowedTools"]
