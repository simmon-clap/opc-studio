"""Supervisor — link commitments to tasks and record workflow telemetry."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.orchestrator.dispatch_planner import DispatchPlan
from app.services.commitments import (
    close_commitments_for_task,
    link_commitment_artifact,
    link_commitment_task,
    list_commitments,
    open_commitment,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def link_open_commitments_to_task(
    dashboard: dict[str, Any],
    *,
    project_id: str,
    task_id: str,
    owner_role: str,
) -> None:
    for item in list_commitments(dashboard, status="open", project_id=project_id):
        if item.get("ownerRole") == owner_role and not item.get("linkedTaskId"):
            link_commitment_task(dashboard, item["id"], task_id)


def on_task_completed(
    dashboard: dict[str, Any], task_id: str, artifact_id: str | None
) -> None:
    close_commitments_for_task(dashboard, task_id)
    if artifact_id:
        for item in list_commitments(dashboard, status="open"):
            if item.get("linkedTaskId") == task_id:
                link_commitment_artifact(dashboard, item["id"], artifact_id)


def on_task_failed(
    dashboard: dict[str, Any],
    *,
    project_id: str,
    task_id: str,
    owner_role: str,
    reason: str,
) -> None:
    open_commitment(
        dashboard,
        project_id=project_id,
        what=f"任务失败需重试：{reason[:60]}",
        owner_role=owner_role,
        kind="retry",
        source=f"task:{task_id}",
    )


def record_workflow_run(
    dashboard: dict[str, Any],
    *,
    project_id: str,
    plan: DispatchPlan | None,
    status: str,
    error: str | None = None,
) -> None:
    meta = dashboard.setdefault("meta", {})
    meta["lastWorkflowRun"] = {
        "at": _now_iso(),
        "projectId": project_id,
        "status": status,
        "shouldDispatch": bool(plan and plan.should_dispatch),
        "mode": plan.mode if plan else "none",
        "reason": plan.reason if plan else "",
        "error": error,
    }
