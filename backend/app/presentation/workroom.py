"""Workroom v2 presenter — nav groups, focus, project header."""

from __future__ import annotations

from typing import Any

from app.deliverables.kinds import GROUP_LABELS, KIND_REGISTRY
from app.orchestrator.workflow_engine import get_focus_and_others
from app.presentation.artifact_actions import (
    artifact_actions,
    artifact_export_formats,
    artifact_status_dot,
)
from app.presentation.project_progress import (
    artifact_group_id,
    compute_project_progress,
    roles_for_group,
)
from app.services.project_briefs import get_brief

ART_GROUP_ORDER = ["evaluate", "legal", "engineering", "delivery", "ops"]


def _enrich_artifact(art: dict[str, Any]) -> dict[str, Any]:
    row = {k: v for k, v in art.items() if k != "content"}
    row["group"] = artifact_group_id(art)
    row["statusDot"] = artifact_status_dot(art)
    row["actions"] = artifact_actions(art)
    row["exportFormats"] = artifact_export_formats(art)
    return row


def _closure_tag(project_id: str, dashboard: dict[str, Any]) -> str | None:
    closure = (dashboard.get("closure") or {}).get(project_id)
    if not closure or closure.get("status") == "closed":
        return None
    status = closure.get("status") or ""
    labels = {
        "awaiting_hitl": "待 HITL 结项",
        "in_closure": "结项中",
        "pending": "待结项",
    }
    return labels.get(status, status)


def build_workroom_payload(
    dashboard: dict[str, Any],
    project_id: str,
    *,
    deliberation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    project = next(
        (p for p in dashboard.get("projects", []) if p.get("id") == project_id),
        None,
    )
    if not project:
        return {}

    progress = compute_project_progress(dashboard, project)
    brief = get_brief(dashboard, project_id)
    open_questions = list(brief.get("openQuestions") or [])
    arts = [
        _enrich_artifact(a)
        for a in dashboard.get("artifacts", [])
        if a.get("projectId") == project_id
    ]

    by_group: dict[str, list[dict[str, Any]]] = {g: [] for g in ART_GROUP_ORDER}
    for art in arts:
        by_group.setdefault(artifact_group_id(art), []).append(art)

    current_group = progress.get("currentStageGroup") or "evaluate"
    closure = (dashboard.get("closure") or {}).get(project_id)
    groups = []
    for gid in ART_GROUP_ORDER:
        items = by_group.get(gid) or []
        fold: list[dict[str, Any]] = []
        if gid == "evaluate" and open_questions:
            fold.append(
                {
                    "type": "brief",
                    "label": f"Brief · {len(open_questions)} 项待确认",
                    "openQuestions": open_questions,
                    "brief": brief,
                    "roles": ["ceo"],
                }
            )
        if gid == "evaluate" and deliberation and deliberation.get("turns"):
            delib_roles = sorted(
                {t.get("author") for t in deliberation.get("turns", []) if t.get("author")}
            )
            fold.append(
                {
                    "type": "deliberation",
                    "label": f"CEO 会诊 · {'进行中' if deliberation.get('status') == 'open' else '已收口'}",
                    "data": deliberation,
                    "roles": delib_roles,
                }
            )
        closure_data = closure
        if gid == "delivery" and closure_data:
            done = sum(1 for x in closure_data.get("checklist", []) if x.get("done"))
            total = len(closure_data.get("checklist") or [])
            closure_roles = sorted(
                {
                    item.get("roleId")
                    for item in closure_data.get("checklist", [])
                    if item.get("roleId")
                }
            )
            fold.append(
                {
                    "type": "closure",
                    "label": f"结项清单 · {done}/{total}",
                    "data": closure_data,
                    "roles": closure_roles,
                }
            )
        group_roles = roles_for_group(dashboard, project_id, gid)
        if items or fold or gid in {"evaluate", "legal"}:
            groups.append(
                {
                    "id": gid,
                    "label": GROUP_LABELS.get(gid, gid),
                    "artifacts": items,
                    "fold": fold,
                    "isCurrent": gid == current_group,
                    "isHistory": gid != current_group,
                    "roles": group_roles,
                }
            )

    focus, others = get_focus_and_others(dashboard, project_id)
    closure_tag = _closure_tag(project_id, dashboard)
    costs_rows = (dashboard.get("costs") or {}).get("byProject") or []
    if isinstance(costs_rows, dict):
        pnl = costs_rows.get(project_id) or {}
    else:
        pnl = next((r for r in costs_rows if r.get("projectId") == project_id), {})

    header = {
        "clientName": (project.get("clientName") or project_id).replace("（线索）", ""),
        "stage": project.get("stage") or "",
        "stageShort": progress.get("stageShort") or "",
        "progress": progress.get("progress") or 0,
        "progressDetail": progress,
        "pipelineColumn": project.get("pipelineColumn") or "",
        "hitlPending": project.get("hitlPending"),
        "priority": project.get("priority") or "P2",
        "summary": project.get("summary") or "",
        "agentDeliverable": project.get("agentDeliverable") or "",
        "assignees": list(project.get("assignees") or []),
        "closureTag": closure_tag,
        "pnlHealth": pnl.get("health"),
        "projectId": project_id,
        "currentStageGroup": current_group,
    }

    export_menu = [{"id": "internal", "label": "内部完整包 ZIP"}]
    if closure and closure.get("status") in {"in_closure", "closed"}:
        export_menu.append({"id": "client", "label": "客户交付包 ZIP"})

    return {
        "header": header,
        "groups": groups,
        "focus": focus,
        "others": others,
        "exportMenu": export_menu,
        "kindGroups": {k: v["group"] for k, v in KIND_REGISTRY.items()},
    }
