"""Task-related agency rules."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.agency.signals import Signal


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _task_anchor(task: dict[str, Any]) -> datetime | None:
    activities = task.get("activities") or []
    if activities:
        return _parse_iso(activities[-1].get("at"))
    return _parse_iso(task.get("startedAt") or task.get("queuedAt"))


def observe_task_health(
    dashboard: dict[str, Any],
    *,
    role_id: str | None = None,
    stale_min: int = 30,
) -> list[Signal]:
    now = datetime.now(timezone.utc)
    signals: list[Signal] = []

    for task in dashboard.get("tasks", []):
        if role_id and task.get("roleId") != role_id:
            continue
        tid = task.get("roleId") or "ceo"
        project_id = task.get("projectId")
        title = task.get("title") or "任务"

        if task.get("status") == "failed":
            if task.get("_agencyFailedHandled"):
                continue
            signals.append(
                Signal(
                    signal_type="task.failed",
                    role_id=tid,
                    project_id=project_id,
                    priority="high",
                    title=f"任务失败 · {title[:40]}",
                    preview=f"{tid} · {project_id}",
                    fingerprint=f"task.failed:{task.get('id')}",
                    risk_level="medium",
                    suggested_action="review",
                )
            )
            continue

        if task.get("status") != "running":
            continue
        anchor = _task_anchor(task)
        if not anchor:
            continue
        age_min = (now - anchor.astimezone(timezone.utc)).total_seconds() / 60.0
        if age_min < stale_min:
            continue
        signals.append(
            Signal(
                signal_type="task.stuck",
                role_id=tid,
                project_id=project_id,
                priority="high",
                title=f"任务卡住 · {title[:40]}",
                preview=f"running {int(age_min)}min · {project_id}",
                fingerprint=f"task.stuck:{task.get('id')}",
                risk_level="medium",
                suggested_action="review",
            )
        )

    return signals


def observe_role_failed_for_ceo(
    dashboard: dict[str, Any], role_id: str
) -> list[Signal]:
    signals: list[Signal] = []
    for task in dashboard.get("tasks", []):
        if task.get("roleId") != role_id or task.get("status") != "failed":
            continue
        signals.append(
            Signal(
                signal_type="my.failed",
                role_id=role_id,
                project_id=task.get("projectId"),
                priority="high",
                title=f"建议 CEO 关注：{task.get('title', '失败任务')[:40]}",
                preview=f"{role_id} 任务失败",
                fingerprint=f"my.failed:{task.get('id')}",
                risk_level="medium",
                suggested_action="review",
            )
        )
    return signals
