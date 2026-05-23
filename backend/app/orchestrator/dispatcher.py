"""Task dispatch helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.services.dispatch_feed import log_assign


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def dispatch_task(
    dashboard: dict[str, Any],
    *,
    role_id: str,
    project_id: str,
    title: str,
    status: str = "pending",
    priority: str = "normal",
    deliverable_kind: str | None = None,
) -> dict[str, Any]:
    now = _now_iso()
    task_id = f"task-{role_id}-{uuid4().hex[:6]}"
    task = {
        "id": task_id,
        "roleId": role_id,
        "projectId": project_id,
        "title": title,
        "status": status,
        "priority": priority,
        "activities": [
            {
                "id": f"act-{uuid4().hex[:8]}",
                "at": now,
                "message": f"Orchestrator Dispatch: {title}",
            }
        ],
    }
    if status == "pending":
        task["queuedAt"] = now
    else:
        task["startedAt"] = now
    if deliverable_kind:
        task["deliverableKind"] = deliverable_kind
    dashboard.setdefault("tasks", []).insert(0, task)
    if role_id != "ceo":
        log_assign(
            dashboard,
            to_role=role_id,
            title=title,
            project_id=project_id,
            task_id=task_id,
        )
    return task


def claim_task_running(dashboard: dict[str, Any], task: dict[str, Any]) -> None:
    now = _now_iso()
    task["status"] = "running"
    task["startedAt"] = now
    task.setdefault("activities", []).append(
        {
            "id": f"act-{uuid4().hex[:8]}",
            "at": now,
            "message": "Pulse：开始执行",
        }
    )


def complete_task(dashboard: dict[str, Any], task_id: str, note: str) -> dict[str, Any] | None:
    for task in dashboard.get("tasks", []):
        if task.get("id") == task_id:
            task["status"] = "done"
            task["completedAt"] = _now_iso()
            task.setdefault("activities", []).append(
                {
                    "id": f"act-{uuid4().hex[:8]}",
                    "at": _now_iso(),
                    "message": note,
                }
            )
            return task
    return None
