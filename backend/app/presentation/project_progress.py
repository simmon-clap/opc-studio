"""Derived project progress — stage + execution, not a static mock field."""

from __future__ import annotations

import re
from typing import Any

from app.deliverables.kinds import GROUP_LABELS, KIND_REGISTRY

STAGE_TO_GROUP: dict[int, str] = {
    1: "evaluate",
    2: "evaluate",
    3: "legal",
    4: "engineering",
    5: "delivery",
}

GROUP_ORDER = ["evaluate", "legal", "engineering", "delivery", "ops"]


def parse_stage_index(stage: str | None) -> int:
    if not stage:
        return 1
    m = re.search(r"阶段\s*(\d)", stage)
    if m:
        return max(1, min(5, int(m.group(1))))
    if "结项" in stage or "交付" in stage and "开发" not in stage:
        return 5
    return 1


def artifact_group_id(art: dict[str, Any]) -> str:
    if art.get("group"):
        return art["group"]
    kind = art.get("kind") or art.get("type") or "doc"
    meta = KIND_REGISTRY.get(kind) or KIND_REGISTRY["doc"]
    return meta["group"]


def _artifact_weight(art: dict[str, Any]) -> float:
    status = art.get("status") or "draft"
    pending = int(
        art.get("pendingFields")
        or (art.get("quality") or {}).get("pendingFields")
        or 0
    )
    if status == "approved":
        return 1.0
    if status == "review":
        return 0.85
    if status == "revision":
        return 0.45
    if pending > 0:
        return 0.25
    return 0.5


def compute_project_progress(
    dashboard: dict[str, Any], project: dict[str, Any]
) -> dict[str, Any]:
    pid = project.get("id") or ""
    stage_idx = parse_stage_index(project.get("stage"))
    current_group = STAGE_TO_GROUP.get(stage_idx, "evaluate")

    arts = [
        a
        for a in dashboard.get("artifacts", [])
        if a.get("projectId") == pid
    ]
    tasks = [
        t
        for t in dashboard.get("tasks", [])
        if t.get("projectId") == pid
    ]
    running = [t for t in tasks if t.get("status") == "running"]
    pending = [t for t in tasks if t.get("status") == "pending" and not t.get("waitingOn")]

    group_weights: dict[str, list[float]] = {g: [] for g in GROUP_ORDER}
    for art in arts:
        gid = artifact_group_id(art)
        group_weights.setdefault(gid, []).append(_artifact_weight(art))

    group_completion: dict[str, float] = {}
    for gid, weights in group_weights.items():
        group_completion[gid] = sum(weights) / len(weights) if weights else 0.0

    stage_base = (stage_idx - 1) * 20
    current_group_pct = round(group_completion.get(current_group, 0) * 20)
    progress = min(100, stage_base + current_group_pct)

    if project.get("pipelineColumn") == "done" or stage_idx >= 5:
        closure = (dashboard.get("closure") or {}).get(pid) or {}
        checklist = closure.get("checklist") or []
        if checklist:
            done = sum(1 for x in checklist if x.get("done"))
            progress = min(100, 85 + round((done / len(checklist)) * 15))
        elif project.get("pipelineColumn") == "done":
            progress = 100

    if project.get("hitlPending"):
        progress = min(progress, stage_base + 18)

    exec_pct = None
    exec_note = None
    if running:
        exec_pct = round(sum(int(t.get("progress") or 0) for t in running) / len(running))
        exec_note = running[0].get("progressNote") or running[0].get("title")
        if len(running) > 1:
            exec_note = f"{len(running)} 项执行中 · {(exec_note or '')[:40]}"

    stage_short = re.sub(r"^阶段\d\s*[·.]?\s*", "", project.get("stage") or "") or "—"

    return {
        "progress": progress,
        "stageIndex": stage_idx,
        "stageLabel": project.get("stage") or "",
        "stageShort": stage_short,
        "currentStageGroup": current_group,
        "executionProgress": exec_pct,
        "executionNote": exec_note,
        "pendingTaskCount": len(pending),
        "runningTaskCount": len(running),
        "artifactApproved": sum(1 for a in arts if a.get("status") == "approved"),
        "artifactTotal": len(arts),
        "groupCompletion": group_completion,
    }


def recompute_projects_progress(dashboard: dict[str, Any]) -> None:
    for project in dashboard.get("projects") or []:
        detail = compute_project_progress(dashboard, project)
        project["progress"] = detail["progress"]
        project["progressDetail"] = {
            k: v for k, v in detail.items() if k != "progress"
        }


def roles_for_group(
    dashboard: dict[str, Any],
    project_id: str,
    group_id: str,
) -> list[str]:
    roles: set[str] = set()
    for art in dashboard.get("artifacts") or []:
        if art.get("projectId") != project_id:
            continue
        if artifact_group_id(art) == group_id and art.get("roleId"):
            roles.add(art["roleId"])
    stage_prefix = {
        "evaluate": ("阶段1", "阶段2", "线索", "评估"),
        "legal": ("阶段3", "签约", "方案"),
        "engineering": ("阶段4", "开发", "交付"),
        "delivery": ("阶段5", "验收", "结项"),
        "ops": ("运营", "台账", "并行"),
    }.get(group_id, ())
    for task in dashboard.get("tasks") or []:
        if task.get("projectId") != project_id:
            continue
        stage = task.get("stage") or ""
        if any(k in stage for k in stage_prefix) and task.get("roleId"):
            roles.add(task["roleId"])
    return sorted(roles)
