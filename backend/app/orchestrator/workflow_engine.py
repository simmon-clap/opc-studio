"""Project workflow next-steps — proactive process cues."""

from __future__ import annotations

from typing import Any

from app.services.project_briefs import get_brief

TYPE_ORDER = {
    "hitl": 0,
    "fill": 1,
    "running": 2,
    "pending": 3,
    "question": 4,
    "commitment": 5,
    "process": 6,
}


def _client_label(project: dict[str, Any], project_id: str) -> str:
    return (project.get("clientName") or project_id).replace("（线索）", "")


def collect_workflow_steps(dashboard: dict[str, Any], project_id: str) -> list[dict[str, Any]]:
    project = next(
        (p for p in dashboard.get("projects", []) if p.get("id") == project_id),
        None,
    )
    if not project:
        return []

    steps: list[dict[str, Any]] = []
    brief = get_brief(dashboard, project_id)
    client = _client_label(project, project_id)
    arts = [a for a in dashboard.get("artifacts", []) if a.get("projectId") == project_id]

    if project.get("hitlPending"):
        hitl_label = project["hitlPending"]
        hitl_item = next(
            (
                h
                for h in dashboard.get("hitlQueue", [])
                if h.get("projectId") == project_id
                and (
                    h.get("type") == hitl_label
                    or h.get("id") == hitl_label
                    or hitl_label in (h.get("title") or "")
                )
            ),
            None,
        )
        review_art = next(
            (a for a in arts if a.get("status") == "review" and a.get("hitlId")),
            None,
        )
        steps.append(
            {
                "type": "hitl",
                "priority": "high",
                "message": hitl_item.get("title") if hitl_item else f"{client}：{hitl_label} 待你审批",
                "hitlId": (review_art or {}).get("hitlId") or (hitl_item or {}).get("id"),
                "artifactId": (review_art or {}).get("id"),
            }
        )

    for art in arts:
        pending = int(
            art.get("pendingFields")
            or (art.get("quality") or {}).get("pendingFields")
            or 0
        )
        if pending > 0 and art.get("status") in {None, "draft", "revision"}:
            steps.append(
                {
                    "type": "fill",
                    "priority": "high",
                    "message": f"{art.get('title') or '交付物'} · {pending} 处待填写",
                    "artifactId": art.get("id"),
                }
            )

    for q in brief.get("openQuestions") or []:
        steps.append(
            {
                "type": "question",
                "priority": "high",
                "message": f"{client}：待你确认 — {q}",
            }
        )

    tasks = [
        t
        for t in dashboard.get("tasks", [])
        if t.get("projectId") == project_id and t.get("status") in {"running", "pending"}
    ]
    for task in tasks:
        role = task.get("roleId") or "agent"
        if task.get("status") == "running":
            note = task.get("progressNote") or task.get("title") or ""
            steps.append(
                {
                    "type": "running",
                    "priority": "medium",
                    "message": f"{role} 执行中 · {note}",
                    "taskId": task.get("id"),
                }
            )
        elif not task.get("waitingOn"):
            steps.append(
                {
                    "type": "pending",
                    "priority": "medium",
                    "message": f"{role} 队列 · {task.get('title') or ''}",
                    "taskId": task.get("id"),
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

    steps.sort(key=lambda s: (TYPE_ORDER.get(s.get("type") or "process", 99), s.get("message") or ""))
    return steps


def get_focus_and_others(
    dashboard: dict[str, Any], project_id: str
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    steps = collect_workflow_steps(dashboard, project_id)
    if not steps:
        return None, []
    return steps[0], steps[1:]


def get_next_steps(dashboard: dict[str, Any], project_id: str) -> list[dict[str, Any]]:
    return collect_workflow_steps(dashboard, project_id)
