"""Project workflow next-steps — proactive process cues."""

from __future__ import annotations

from typing import Any

from app.services.project_briefs import get_brief


def get_next_steps(dashboard: dict[str, Any], project_id: str) -> list[dict[str, Any]]:
    project = next(
        (p for p in dashboard.get("projects", []) if p.get("id") == project_id),
        None,
    )
    if not project:
        return []

    steps: list[dict[str, Any]] = []
    brief = get_brief(dashboard, project_id)
    client = (project.get("clientName") or project_id).replace("（线索）", "")

    for q in brief.get("openQuestions") or []:
        steps.append(
            {
                "type": "question",
                "priority": "high",
                "message": f"{client}：待你确认 — {q}",
            }
        )

    open_cmts = [
        c
        for c in dashboard.get("commitments", [])
        if c.get("projectId") == project_id and c.get("status") == "open"
    ]
    for c in open_cmts:
        steps.append(
            {
                "type": "commitment",
                "priority": "medium",
                "message": f"{c.get('ownerRole')} · {c.get('what')}",
                "commitmentId": c.get("id"),
            }
        )

    stage = project.get("stage") or ""
    pipeline = project.get("pipelineColumn") or ""
    arts = [a for a in dashboard.get("artifacts", []) if a.get("projectId") == project_id]
    has_prd = any((a.get("kind") or "") == "prd" for a in arts)
    has_nda = any(
        (a.get("kind") or "") == "nda" or "nda" in (a.get("title") or "").lower() for a in arts
    )

    if pipeline in {"lead", "clarify"} and not has_prd:
        steps.append(
            {
                "type": "process",
                "priority": "medium",
                "message": f"{client}：可推进 PRD 初稿或立项评估",
            }
        )
    if has_nda and not project.get("hitlPending"):
        nda = next(
            (a for a in arts if (a.get("kind") or "") == "nda" or "nda" in (a.get("title") or "").lower()),
            None,
        )
        if nda and nda.get("status") not in {"approved", "review"}:
            steps.append(
                {
                    "type": "process",
                    "priority": "low",
                    "message": f"{client}：NDA 已定稿可提交你审批",
                    "artifactId": nda.get("id"),
                }
            )

    if "阶段5" in stage or project.get("pipelineColumn") == "done":
        steps.append(
            {
                "type": "process",
                "priority": "low",
                "message": f"{client}：可安排结项与续费跟进",
            }
        )

    return steps
