"""Recompute derived dashboard fields from projects and inbox."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _task_sort_key(task: dict[str, Any]) -> str:
    completed = task.get("completedAt")
    if not completed and task.get("status") == "done":
        activities = task.get("activities") or []
        if activities:
            completed = activities[-1].get("at")
        completed = completed or task.get("startedAt")
    return completed or task.get("startedAt") or task.get("id") or ""


def _sorted_tasks(tasks: list[dict[str, Any]], *, reverse: bool = True) -> list[dict[str, Any]]:
    return sorted(tasks, key=_task_sort_key, reverse=reverse)


def _pending_next(pending: list[dict[str, Any]]) -> dict[str, Any]:
    """Prefer actionable pending tasks over blocked ones waiting on dependencies."""
    return sorted(
        pending,
        key=lambda t: (bool(t.get("dependsOn")), t.get("waitingOn") or "", _task_sort_key(t)),
    )[0]


def _recompute_role_extras(
    role_id: str,
    extras: dict[str, Any],
    *,
    running: list[dict[str, Any]],
    pending: list[dict[str, Any]],
    role_tasks: list[dict[str, Any]],
    done_recent: list[dict[str, Any]],
    projects_by_id: dict[str, dict[str, Any]],
) -> None:
    extras["taskRunning"] = len(running)
    extras["taskPending"] = len(pending)
    extras["taskDoneRecent"] = len(done_recent)

    if role_id == "ceo":
        extras["hitlPending"] = sum(
            1 for p in projects_by_id.values() if p.get("hitlPending")
        )
        extras["openLeads"] = sum(
            1 for p in projects_by_id.values() if p.get("pipelineColumn") == "lead"
        )
    elif role_id == "product":
        extras["prdRunning"] = len(running)
    elif role_id == "ops":
        extras["pipelineLeads"] = sum(
            1 for p in projects_by_id.values() if p.get("pipelineColumn") == "lead"
        )
    elif role_id == "legal":
        extras["quotesPending"] = sum(
            1
            for t in pending
            if any(k in (t.get("title") or "") for k in ("报价", "SOW"))
        )
        flags: list[str] = []
        for t in _sorted_tasks(running + pending + done_recent[:5]):
            title = t.get("title") or ""
            if not any(
                k in title for k in ("合规", "PII", "数据处理", "NDA", "保密", "SOW", "合同")
            ):
                continue
            project = projects_by_id.get(t.get("projectId", ""), {})
            client = (project.get("clientName") or t.get("projectId", "")).replace(
                "（线索）", ""
            )
            status = {"running": "进行中", "pending": "排队", "done": "已完成"}.get(
                t.get("status", ""), ""
            )
            flags.append(f"{client} · {title[:36]}" + (f"（{status}）" if status else ""))
        extras["complianceFlags"] = flags[:6]


def _project_map(dashboard: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {p["id"]: p for p in dashboard.get("projects", []) if p.get("id")}


def recompute_pulse(dashboard: dict[str, Any]) -> None:
    projects = dashboard.get("projects", [])
    pulse = dashboard.setdefault("pulse", {})
    pulse["activeProjects"] = sum(
        1 for p in projects if p.get("pipelineColumn") == "active"
    )
    pulse["hitlPending"] = sum(1 for p in projects if p.get("hitlPending"))
    pulse["alerts"] = len(dashboard.get("alerts", []))
    pulse["leads"] = sum(1 for p in projects if p.get("pipelineColumn") == "lead")


def recompute_stats(dashboard: dict[str, Any]) -> None:
    projects = dashboard.get("projects", [])
    stats = dashboard.setdefault("stats", {})

    def count_column(column: str) -> int:
        if column == "hitl":
            return sum(1 for p in projects if p.get("hitlPending"))
        return sum(1 for p in projects if p.get("pipelineColumn") == column)

    mapping = {
        "leads": "lead",
        "active": "active",
        "clarify": "clarify",
        "hitl": "hitl",
        "done": "done",
    }
    for key, column in mapping.items():
        if key in stats:
            stats[key]["value"] = count_column(column)


def recompute_role_counts(dashboard: dict[str, Any]) -> None:
    tasks = dashboard.get("tasks", [])
    for role in dashboard.get("roles", []):
        role_id = role.get("id")
        role["runningCount"] = sum(
            1 for t in tasks if t.get("roleId") == role_id and t.get("status") == "running"
        )
        role["pendingCount"] = sum(
            1 for t in tasks if t.get("roleId") == role_id and t.get("status") == "pending"
        )


def recompute_role_live_state(dashboard: dict[str, Any]) -> None:
    """Derive workStatus, focus, load, projectIds from tasks + projects."""
    tasks = dashboard.get("tasks", [])
    projects_by_id = _project_map(dashboard)

    for role in dashboard.get("roles", []):
        role_id = role.get("id")
        role_tasks = [t for t in tasks if t.get("roleId") == role_id]
        running = [t for t in role_tasks if t.get("status") == "running"]
        pending = [t for t in role_tasks if t.get("status") == "pending"]
        done_recent = _sorted_tasks(
            [t for t in role_tasks if t.get("status") == "done"]
        )

        role["runningCount"] = len(running)
        role["pendingCount"] = len(pending)

        load = role.setdefault("load", {"current": 0, "max": 3})
        max_load = int(load.get("max") or 3)
        load["current"] = min(len(running) + len(pending), max_load)

        project_ids: set[str] = set(role.get("projectIds") or [])
        for task in running + pending + done_recent[:5]:
            pid = task.get("projectId")
            if pid:
                project_ids.add(pid)
        for project in dashboard.get("projects", []):
            if role_id in (project.get("assignees") or []):
                project_ids.add(project["id"])
        role["projectIds"] = sorted(project_ids)

        if any(t.get("status") == "blocked" for t in role_tasks):
            role["workStatus"] = "blocked"
        elif running:
            role["workStatus"] = "working"
        elif pending:
            if all(t.get("waitingOn") for t in pending):
                role["workStatus"] = "waiting"
            else:
                role["workStatus"] = "working"
        else:
            role["workStatus"] = "idle"

        if running:
            task = _sorted_tasks(running)[0]
            project = projects_by_id.get(task.get("projectId", ""), {})
            client = (project.get("clientName") or "").replace("（线索）", "")
            title = task.get("title") or "进行中任务"
            role["focus"] = f"{title}" + (f" · {client}" if client else "")
            role["lastActiveAt"] = task.get("startedAt") or _now_iso()
        elif pending:
            parts: list[str] = []
            if done_recent:
                latest_done = done_recent[0]
                completed_at = _parse_iso(
                    latest_done.get("completedAt")
                    or ((latest_done.get("activities") or [{}])[-1].get("at"))
                )
                recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
                if completed_at and completed_at.astimezone(timezone.utc) >= recent_cutoff:
                    parts.append(
                        f"刚完成 · {(latest_done.get('title') or '任务')[:36]}"
                    )
                    role["lastActiveAt"] = latest_done.get("completedAt") or role.get(
                        "lastActiveAt"
                    )
            nxt = _pending_next(pending)
            parts.append(
                f"队列 {len(pending)} 项 · 下一项：{(nxt.get('title') or '待执行')[:36]}"
            )
            role["focus"] = " · ".join(parts)
        elif done_recent:
            latest = done_recent[0]
            role["focus"] = f"刚完成 · {(latest.get('title') or '任务')[:48]}"
            role["lastActiveAt"] = latest.get("completedAt") or role.get("lastActiveAt")
        else:
            role["focus"] = "待命 — 暂无进行中任务"

        _recompute_role_extras(
            role_id,
            role.setdefault("extras", {}),
            running=running,
            pending=pending,
            role_tasks=role_tasks,
            done_recent=done_recent,
            projects_by_id=projects_by_id,
        )


from app.presentation.derived import recompute_presentation
from app.presentation.project_progress import recompute_projects_progress


from app.services.budget_alerts import maybe_escalate_budget
from app.presentation.finance import sync_finance


def recompute_finance_extras(dashboard: dict[str, Any]) -> None:
    sync_finance(dashboard)
    maybe_escalate_budget(dashboard)
    costs = dashboard.setdefault("costs", {})
    by_cap: dict[str, float] = {"text": 0.0, "image": 0.0, "video": 0.0, "code": 0.0}
    for run in dashboard.get("agentRuns") or []:
        cap = run.get("capability") or "text"
        cost = float(run.get("costCny") or run.get("cost_cny") or 0)
        by_cap[cap] = by_cap.get(cap, 0.0) + cost
    costs["byCapability"] = [{"capability": k, "cost": round(v, 2)} for k, v in by_cap.items() if v > 0]


def recompute_all(dashboard: dict[str, Any]) -> None:
    recompute_projects_progress(dashboard)
    recompute_pulse(dashboard)
    recompute_stats(dashboard)
    recompute_role_live_state(dashboard)
    recompute_presentation(dashboard)
    recompute_finance_extras(dashboard)
