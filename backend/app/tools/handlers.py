"""Tool handler implementations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.services.founder_profile import get_profile
from app.tools.registry import ToolExecutionContext


async def read_project_brief(args: dict[str, Any], ctx: ToolExecutionContext) -> dict[str, Any]:
    pid = args.get("projectId") or ctx.project_id
    project = next(
        (p for p in ctx.dashboard.get("projects", []) if p.get("id") == pid),
        {},
    )
    brief = (ctx.dashboard.get("projectBriefs") or {}).get(pid) or {}
    return {
        "projectId": pid,
        "clientName": project.get("clientName"),
        "stage": project.get("stage"),
        "brief": brief,
    }


async def write_artifact_file(args: dict[str, Any], ctx: ToolExecutionContext) -> dict[str, Any]:
    pid = args.get("projectId") or ctx.project_id
    title = (args.get("title") or "交付物")[:120]
    content = args.get("content") or ""
    kind = args.get("kind") or "doc"
    artifact_id = f"art-tool-{uuid4().hex[:8]}"
    artifact = {
        "id": artifact_id,
        "projectId": pid,
        "roleId": ctx.role_id,
        "title": title,
        "type": kind,
        "kind": kind,
        "format": "markdown",
        "status": "draft",
        "content": content,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "source": "tool:write_artifact_file",
    }
    ctx.dashboard.setdefault("artifacts", []).append(artifact)
    return {"artifactId": artifact_id, "title": title}


async def read_template(args: dict[str, Any], ctx: ToolExecutionContext) -> dict[str, Any]:
    from app.deliverables.templates import get_template

    tpl_id = args.get("templateId") or "legal.nda_mutual"
    tpl = get_template(tpl_id)
    return {"templateId": tpl_id, "skeleton": tpl.skeleton[:4000]}


async def update_pipeline(args: dict[str, Any], ctx: ToolExecutionContext) -> dict[str, Any]:
    pid = args.get("projectId") or ctx.project_id
    column = args.get("column") or "active"
    project = next(
        (p for p in ctx.dashboard.get("projects", []) if p.get("id") == pid),
        None,
    )
    if project is None:
        return {"ok": False, "error": "PROJECT_NOT_FOUND"}
    project["pipelineColumn"] = column
    return {"ok": True, "projectId": pid, "column": column}


async def read_founder_profile(args: dict[str, Any], ctx: ToolExecutionContext) -> dict[str, Any]:
    profile = get_profile(ctx.dashboard)
    doc = (profile.get("document") or "")[:3000]
    return {"document": doc, "communication": profile.get("communication")}


async def propose_skill_install(args: dict[str, Any], ctx: ToolExecutionContext) -> dict[str, Any]:
    """CEO tool — creates inbox skill_proposal (Epic 3 expands)."""
    markdown = args.get("skillMarkdown") or ""
    title = args.get("title") or "Skill 安装提案"
    item_id = f"inbox-skill-{uuid4().hex[:8]}"
    item = {
        "id": item_id,
        "category": "skill_proposal",
        "title": title,
        "preview": markdown[:400],
        "status": "active",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "proposedSkill": {"rawMarkdown": markdown[:8000]},
        "actions": ["approve_install", "reject"],
    }
    ctx.dashboard.setdefault("inbox", []).insert(0, item)
    return {"inboxId": item_id, "title": title}


async def dispatch_task(args: dict[str, Any], ctx: ToolExecutionContext) -> dict[str, Any]:
    from app.presentation.roles_registry import dispatchable_role_ids
    from app.orchestrator.dispatcher import dispatch_task as _dispatch

    role_id = (args.get("roleId") or "").lower()
    if ctx.role_id != "ceo":
        return {"ok": False, "error": "DISPATCH_CEO_ONLY"}
    if role_id not in dispatchable_role_ids(ctx.dashboard):
        return {"ok": False, "error": "ROLE_NOT_DISPATCHABLE"}
    pid = args.get("projectId") or ctx.project_id
    title = (args.get("title") or "任务")[:80]
    task = _dispatch(
        ctx.dashboard,
        role_id=role_id,
        project_id=pid,
        title=title,
        deliverable_kind=args.get("kind") or role_id,
    )
    return {"ok": True, "taskId": task.get("id"), "roleId": role_id}
