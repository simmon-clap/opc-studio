"""Backfill studio artifacts for completed tasks missing deliverables."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from app.deliverables.artifact_builder import build_artifact_record
from app.deliverables.kinds import resolve_deliverable
from app.deliverables.templates import get_template
from app.services.project_store import write_artifact_file


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _task_has_artifact(dashboard: dict[str, Any], task: dict[str, Any]) -> bool:
    project_id = task.get("projectId")
    role_id = task.get("roleId")
    kind = task.get("deliverableKind") or resolve_deliverable(
        role_id or "",
        task.get("title") or "",
        directive_kind=task.get("deliverableKind"),
    ).kind
    title = (task.get("title") or "").lower()
    for art in dashboard.get("artifacts", []):
        if art.get("projectId") != project_id or art.get("roleId") != role_id:
            continue
        if art.get("kind") == kind:
            return True
        if art.get("taskId") == task.get("id"):
            return True
        art_title = (art.get("title") or "").lower()
        if kind == "nda" and ("nda" in art_title or "保密" in art_title):
            return True
        if kind == "prd" and "prd" in art_title:
            return True
    return False


def repair_missing_artifacts(dashboard: dict[str, Any]) -> int:
    """Create studio artifacts for done tasks that never persisted deliverables."""
    repaired = 0
    for task in dashboard.get("tasks", []):
        if task.get("status") != "done":
            continue
        if _task_has_artifact(dashboard, task):
            continue
        role_id = task.get("roleId") or ""
        project_id = task.get("projectId") or ""
        spec = resolve_deliverable(
            role_id,
            task.get("title") or "",
            directive_kind=task.get("deliverableKind"),
            brief_context=task.get("briefContext") or "",
        )
        tpl = get_template(spec.template_id)
        digest = hashlib.sha256(f"{task.get('id')}:{task.get('title')}".encode()).hexdigest()[:6]
        art_id = f"art-{spec.kind}-{digest}"
        content = tpl.skeleton
        art = build_artifact_record(
            artifact_id=art_id,
            spec=spec,
            content=content,
            role_id=role_id,
            project_id=project_id,
            task_id=task.get("id"),
        )
        art["status"] = "draft"
        art["quality"]["issues"] = ["由已完成任务自动补全骨架，请让对应 Agent 重新生成定稿"]
        dashboard.setdefault("artifacts", []).insert(0, art)
        write_artifact_file(project_id, art_id, content)
        _ensure_project_assignee(dashboard, project_id, role_id)
        repaired += 1
    return repaired


def _ensure_project_assignee(dashboard: dict[str, Any], project_id: str, role_id: str) -> None:
    project = next(
        (p for p in dashboard.get("projects", []) if p.get("id") == project_id),
        None,
    )
    if not project:
        return
    assignees = project.setdefault("assignees", [])
    if role_id not in assignees:
        assignees.append(role_id)
