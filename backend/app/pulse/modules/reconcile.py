"""Reconcile stale running tasks and feed alignment."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session

from app.services.dashboard_store import get_dashboard, mutate
from app.services.dispatch_feed import sync_dispatch_feed
from app.services.runtime_settings import get_runtime_settings


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _task_last_activity(task: dict[str, Any]) -> datetime | None:
    activities = task.get("activities") or []
    if activities:
        return _parse_iso(activities[-1].get("at"))
    return _parse_iso(task.get("startedAt"))


def tick_reconcile(session: Session) -> dict[str, Any]:
    dashboard = get_dashboard(session)
    settings = get_runtime_settings(dashboard)
    stale_min = int(settings.get("pulse", {}).get("runningStaleMin") or 30)
    now = datetime.now(timezone.utc)
    reset_ids: list[str] = []

    with mutate(session) as dashboard:
        for task in dashboard.get("tasks", []):
            if task.get("status") != "running":
                continue
            last = _task_last_activity(task)
            started = _parse_iso(task.get("startedAt"))
            anchor = last or started
            if not anchor:
                task["status"] = "pending"
                task.pop("startedAt", None)
                reset_ids.append(task.get("id", ""))
                continue
            age_min = (now - anchor.astimezone(timezone.utc)).total_seconds() / 60.0
            if age_min >= stale_min:
                task["status"] = "pending"
                task["queuedAt"] = now.astimezone().isoformat(timespec="seconds")
                task.setdefault("activities", []).append(
                    {
                        "id": f"act-reconcile-{task.get('id')}",
                        "at": task["queuedAt"],
                        "message": f"Reconcile：running 超时 {stale_min}min，重新排队",
                    }
                )
                reset_ids.append(task.get("id", ""))

        sync_dispatch_feed(dashboard)
        meta = dashboard.setdefault("meta", {})
        runtime = meta.setdefault("pulseRuntime", {})
        runtime["lastReconcile"] = now.astimezone().isoformat(timespec="seconds")
        runtime["reconciledTasks"] = reset_ids

    return {"reset": len(reset_ids), "taskIds": reset_ids}
