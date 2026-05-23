"""Project and brief mutations from Workroom."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.services.project_briefs import merge_brief_delta, _now_iso

VALID_PRIORITIES = frozenset({"P0", "P1", "P2", "P3"})
ACTIVE_TASK_STATUSES = frozenset({"running", "pending", "blocked"})


def _find_project(dashboard: dict[str, Any], project_id: str) -> dict[str, Any] | None:
    return next(
        (p for p in dashboard.get("projects", []) if p.get("id") == project_id),
        None,
    )


def _notify_ceo_priority_change(
    dashboard: dict[str, Any],
    project: dict[str, Any],
    old_priority: str,
    new_priority: str,
) -> None:
    client = (project.get("clientName") or project.get("id") or "").replace("（线索）", "")
    dashboard.setdefault("inbox", []).insert(
        0,
        {
            "id": f"inbox-{uuid4().hex[:8]}",
            "category": "request",
            "from": "founder",
            "channel": "web",
            "title": f"优先级调整 · {client} {old_priority} → {new_priority}",
            "preview": f"Founder 将项目优先级调整为 {new_priority}，请同步任务排期与资源分配。",
            "projectId": project.get("id"),
            "at": _now_iso(),
            "read": False,
            "status": "active",
        },
    )
    dashboard.setdefault("dispatchFeed", []).insert(
        0,
        {
            "id": f"feed-{uuid4().hex[:8]}",
            "at": _now_iso(),
            "type": "founder.directive",
            "from": "founder",
            "to": "ceo",
            "projectId": project.get("id"),
            "message": f"项目 {client} 优先级 {old_priority} → {new_priority}",
        },
    )


def _sync_task_priorities(
    dashboard: dict[str, Any], project_id: str, priority: str
) -> int:
    updated = 0
    for task in dashboard.get("tasks") or []:
        if task.get("projectId") != project_id:
            continue
        if task.get("status") not in ACTIVE_TASK_STATUSES:
            continue
        if task.get("priority") != priority:
            task["priority"] = priority
            updated += 1
    return updated


def patch_project(
    dashboard: dict[str, Any],
    project_id: str,
    *,
    priority: str | None = None,
    summary: str | None = None,
    assignees: list[str] | None = None,
) -> dict[str, Any]:
    project = _find_project(dashboard, project_id)
    if not project:
        raise ValueError("PROJECT_NOT_FOUND")

    tasks_updated = 0
    old_priority = project.get("priority") or "P2"

    if priority is not None:
        if priority not in VALID_PRIORITIES:
            raise ValueError("INVALID_PRIORITY")
        if priority != old_priority:
            project["priority"] = priority
            tasks_updated = _sync_task_priorities(dashboard, project_id, priority)
            _notify_ceo_priority_change(dashboard, project, old_priority, priority)

    if summary is not None:
        project["summary"] = summary.strip()

    if assignees is not None:
        project["assignees"] = list(assignees)

    return {
        "project": project,
        "tasksUpdated": tasks_updated,
        "priorityChanged": priority is not None and priority != old_priority,
    }


def patch_project_brief(
    dashboard: dict[str, Any],
    project_id: str,
    delta: dict[str, Any],
) -> dict[str, Any]:
    if not _find_project(dashboard, project_id):
        raise ValueError("PROJECT_NOT_FOUND")
    brief = merge_brief_delta(dashboard, project_id, delta)
    return {"brief": brief, "projectId": project_id}
