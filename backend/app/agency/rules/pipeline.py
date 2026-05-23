"""Pipeline / next-step agency rules."""

from __future__ import annotations

from typing import Any

from app.agency.signals import Signal
from app.orchestrator.workflow_engine import get_next_steps


def observe_pipeline_gaps(
    dashboard: dict[str, Any], *, role_id: str = "ceo"
) -> list[Signal]:
    signals: list[Signal] = []
    for project in dashboard.get("projects", []):
        project_id = project.get("id")
        if not project_id:
            continue
        client = (project.get("clientName") or project_id).replace("（线索）", "")
        for step in get_next_steps(dashboard, project_id):
            step_type = step.get("type") or "process"
            priority = step.get("priority") or "medium"
            message = step.get("message") or ""
            fp_key = step.get("commitmentId") or step.get("artifactId") or message[:40]
            signals.append(
                Signal(
                    signal_type=f"pipeline.{step_type}",
                    role_id=role_id,
                    project_id=project_id,
                    priority=priority,
                    title=f"流程建议 · {client}",
                    preview=message[:120],
                    fingerprint=f"pipeline.{step_type}:{project_id}:{fp_key}",
                    risk_level="low" if step_type == "process" else "medium",
                    suggested_action="dispatch" if step_type == "process" else "review",
                    suggested_role=_suggest_role_for_step(step_type, message),
                    suggested_title=_suggest_title(message),
                )
            )
    return signals


def _suggest_role_for_step(step_type: str, message: str) -> str | None:
    text = message.lower()
    if "nda" in text or "法务" in message:
        return "legal"
    if "prd" in text or "产品" in message:
        return "product"
    if "结项" in message or "续费" in message:
        return "ops"
    if step_type == "process":
        return "product"
    return None


def _suggest_title(message: str) -> str | None:
    if "：" in message:
        return message.split("：", 1)[-1][:60]
    return message[:60] or None
