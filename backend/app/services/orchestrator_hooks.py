"""Async hooks into the orchestrator engine."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def on_hitl_approved(hitl_id: str, project_id: str | None) -> None:
    await _emit("hitl.approved", {"hitlId": hitl_id, "projectId": project_id})


async def on_hitl_rejected(hitl_id: str, project_id: str | None, note: str) -> None:
    await _emit(
        "hitl.rejected",
        {
            "hitlId": hitl_id,
            "projectId": project_id,
            "note": note,
            "artifactId": None,
        },
    )


async def on_inbox_resolved(inbox_id: str, action: str) -> None:
    await _emit("inbox.resolved", {"inboxId": inbox_id, "action": action})


async def on_ceo_brief_chat(
    text: str, attachment_ids: list[str] | None = None
) -> dict[str, Any]:
    from app.db import session_scope
    from app.orchestrator.engine import get_orchestrator

    with session_scope() as session:
        project_id, schedule_workflow = await get_orchestrator().run_ceo_turn_phase(
            session, text, attachment_ids=attachment_ids or []
        )
    return {"projectId": project_id, "scheduleWorkflow": schedule_workflow}


async def on_ceo_brief_plan_and_workflow(
    text: str, project_id: str, attachment_ids: list[str] | None = None
) -> None:
    from app.db import session_scope
    from app.orchestrator.engine import get_orchestrator

    with session_scope() as session:
        await get_orchestrator().run_workflow_phase(session, text, project_id)


async def on_ceo_brief_workflow(text: str, project_id: str) -> None:
    """Legacy alias — plan + execute."""
    await on_ceo_brief_plan_and_workflow(text, project_id)


async def on_ceo_brief(text: str) -> None:
    """Legacy: chat + workflow in one call (tests / sync paths)."""
    meta = await on_ceo_brief_chat(text)
    if meta.get("scheduleWorkflow"):
        await on_ceo_brief_plan_and_workflow(text, meta["projectId"])


async def on_weekly_sent(week: str | None) -> None:
    await _emit("weekly.sent", {"week": week})


async def on_artifact_updated(project_id: str, artifact_id: str) -> None:
    await _emit(
        "artifact.updated",
        {"projectId": project_id, "artifactId": artifact_id},
    )


async def _emit(event_type: str, payload: dict[str, Any]) -> None:
    try:
        from app.orchestrator.engine import get_orchestrator

        orchestrator = get_orchestrator()
        await orchestrator.on_event(event_type, payload)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Orchestrator hook failed: %s", exc)
        raise
