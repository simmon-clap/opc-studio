"""Execute pending tasks — claims queue and runs orchestrator runner."""

from __future__ import annotations

import logging
from typing import Any

from sqlmodel import Session

from app.orchestrator import dispatcher
from app.services import aggregates
from app.services.dashboard_store import get_dashboard, mutate, save
from app.services.runtime_settings import get_runtime_settings

logger = logging.getLogger(__name__)


def _pick_next_pending(dashboard: dict[str, Any]) -> dict[str, Any] | None:
    pending = [t for t in dashboard.get("tasks", []) if t.get("status") == "pending"]
    if not pending:
        return None
    priority_rank = {"urgent": 0, "high": 1, "normal": 2, "low": 3}

    def sort_key(task: dict[str, Any]) -> tuple:
        pr = priority_rank.get(task.get("priority") or "normal", 2)
        return (pr, task.get("queuedAt") or task.get("startedAt") or "", task.get("id") or "")

    return sorted(pending, key=sort_key)[0]


def has_running_task(dashboard: dict[str, Any]) -> bool:
    return any(t.get("status") == "running" for t in dashboard.get("tasks", []))


async def run_one_pending(session: Session) -> dict[str, Any] | None:
    """Claim one pending task and execute it. Returns task id or None."""
    task_id: str | None = None
    with mutate(session) as dashboard:
        if has_running_task(dashboard):
            return None
        task = _pick_next_pending(dashboard)
        if not task:
            return None
        dispatcher.claim_task_running(dashboard, task)
        task_id = task["id"]
        aggregates.recompute_all(dashboard)

    dashboard = get_dashboard(session)
    task = next((t for t in dashboard.get("tasks", []) if t.get("id") == task_id), None)
    if not task:
        return None

    try:
        from app.orchestrator.engine import get_orchestrator

        await get_orchestrator()._execute_runner(session, dashboard, task, skip_thread=True)
        save(session, dashboard)
        with mutate(session) as dashboard:
            aggregates.recompute_all(dashboard)
    except Exception:
        logger.exception("Pulse execution failed for task %s", task_id)
        with mutate(session) as dashboard:
            failed = next(
                (t for t in dashboard.get("tasks", []) if t.get("id") == task_id),
                None,
            )
            if failed and failed.get("status") == "running":
                failed["status"] = "failed"
                failed.setdefault("activities", []).append(
                    {
                        "id": f"act-fail-{task_id}",
                        "at": failed.get("startedAt"),
                        "message": "Pulse 执行异常",
                    }
                )
            aggregates.recompute_all(dashboard)
        raise

    return {"taskId": task_id}


async def drain_pending_queue(session: Session, *, max_tasks: int = 20) -> int:
    """Run up to max_tasks pending items synchronously (workflow drain)."""
    ran = 0
    for _ in range(max_tasks):
        if has_running_task(get_dashboard(session)):
            break
        result = await run_one_pending(session)
        if not result:
            break
        ran += 1
    return ran


async def tick_execution(session: Session) -> dict[str, Any]:
    settings = get_runtime_settings(get_dashboard(session))
    if has_running_task(get_dashboard(session)):
        return {"action": "busy"}
    result = await run_one_pending(session)
    if result:
        return {"action": "ran", **result}
    return {"action": "idle"}
