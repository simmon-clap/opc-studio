"""Agency role modules."""

from __future__ import annotations

from typing import Any

from app.agency.rules import artifacts, pipeline, tasks
from app.agency.signals import Signal


def observe_ceo(dashboard: dict[str, Any], *, stale_min: int = 30) -> list[Signal]:
    signals: list[Signal] = []
    signals.extend(tasks.observe_task_health(dashboard, stale_min=stale_min))
    signals.extend(artifacts.observe_hitl_pending(dashboard))
    signals.extend(artifacts.observe_open_questions(dashboard))
    signals.extend(pipeline.observe_pipeline_gaps(dashboard, role_id="ceo"))
    return signals


def observe_product(dashboard: dict[str, Any]) -> list[Signal]:
    signals = tasks.observe_role_failed_for_ceo(dashboard, "product")
    signals.extend(artifacts.observe_artifact_gaps(dashboard, role_id="product"))
    return signals


def observe_legal(dashboard: dict[str, Any]) -> list[Signal]:
    signals = tasks.observe_role_failed_for_ceo(dashboard, "legal")
    signals.extend(artifacts.observe_artifact_gaps(dashboard, role_id="legal"))
    return signals


def observe_dev(dashboard: dict[str, Any]) -> list[Signal]:
    signals = tasks.observe_role_failed_for_ceo(dashboard, "dev")
    for task in dashboard.get("tasks", []):
        if task.get("roleId") != "dev" or task.get("status") not in {"pending", "blocked"}:
            continue
        if task.get("waitingOn"):
            signals.append(
                Signal(
                    signal_type="deliverable.blocked",
                    role_id="dev",
                    project_id=task.get("projectId"),
                    priority="medium",
                    title=f"开发任务阻塞 · {task.get('title', '')[:36]}",
                    preview=f"等待 {task.get('waitingOn')}",
                    fingerprint=f"deliverable.blocked:{task.get('id')}",
                    risk_level="low",
                    suggested_action="review",
                )
            )
    signals.extend(artifacts.observe_artifact_gaps(dashboard, role_id="dev"))
    return signals


def observe_ops(dashboard: dict[str, Any]) -> list[Signal]:
    signals = tasks.observe_role_failed_for_ceo(dashboard, "ops")
    signals.extend(artifacts.observe_artifact_gaps(dashboard, role_id="ops"))
    return signals


ROLE_OBSERVERS = {
    "ceo": observe_ceo,
    "product": observe_product,
    "legal": observe_legal,
    "dev": observe_dev,
    "ops": observe_ops,
}
