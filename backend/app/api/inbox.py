"""Inbox endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session

from app.api.deps import fail, ok, run_mutation
from app.db import get_session
from app.services import orchestrator_hooks
from app.services.dashboard_store import get_dashboard
from app.services.state_machines import patch_inbox, resolve_inbox
from app.presentation.skills import activate_skill, import_skill

router = APIRouter(tags=["inbox"])


class InboxPatch(BaseModel):
    read: bool | None = None
    status: str | None = None


class ResolveBody(BaseModel):
    action: str


@router.get("/inbox")
def list_inbox(
    category: str | None = None,
    status: str | None = None,
    session: Session = Depends(get_session),
):
    dashboard = get_dashboard(session)
    items = dashboard.get("inbox", [])
    if category:
        items = [i for i in items if i.get("category") == category]
    if status:
        items = [i for i in items if i.get("status") == status]
    return ok(items)


@router.patch("/inbox/{inbox_id}")
def patch_inbox_item(
    inbox_id: str,
    body: InboxPatch,
    session: Session = Depends(get_session),
):
    patch = body.model_dump(exclude_none=True)
    if not patch:
        raise fail("INVALID_PATCH", "无有效更新字段")

    def _apply(dashboard):
        return patch_inbox(dashboard, inbox_id, patch)

    try:
        item, patch = run_mutation(session, _apply, patch_domains=["inbox", "pulse"])
    except ValueError as exc:
        if str(exc) == "INBOX_NOT_FOUND":
            raise fail("INBOX_NOT_FOUND", "收件项不存在", status=404) from exc
        raise
    return ok(item, patch=patch)


@router.post("/inbox/{inbox_id}/resolve")
async def resolve_inbox_item(
    inbox_id: str,
    body: ResolveBody,
    session: Session = Depends(get_session),
):
    if body.action not in {"approve", "discuss"}:
        raise fail("INVALID_ACTION", "action 必须为 approve 或 discuss")

    def _apply(dashboard):
        return resolve_inbox(dashboard, inbox_id, body.action)

    try:
        item, patch = run_mutation(session, _apply, patch_domains=["inbox", "pulse"])
    except ValueError as exc:
        if str(exc) == "INBOX_NOT_FOUND":
            raise fail("INBOX_NOT_FOUND", "收件项不存在", status=404) from exc
        raise

    await orchestrator_hooks.on_inbox_resolved(inbox_id, body.action)
    return ok(item, patch=patch)


@router.post("/inbox/{inbox_id}/skill-install")
def approve_skill_install(inbox_id: str, session: Session = Depends(get_session)):
    """采纳 skill_proposal → import + activate."""

    def _apply(dashboard):
        item = next((i for i in dashboard.get("inbox", []) if i.get("id") == inbox_id), None)
        if item is None:
            raise ValueError("INBOX_NOT_FOUND")
        if item.get("category") != "skill_proposal":
            raise ValueError("INVALID_CATEGORY")
        proposed = item.get("proposedSkill") or {}
        markdown = proposed.get("rawMarkdown") or proposed.get("markdown") or ""
        if not markdown.strip():
            raise ValueError("MISSING_SKILL_DOC")
        try:
            skill = import_skill(dashboard, markdown)
            activate_skill(dashboard, skill["id"])
            skill_id = skill["id"]
        except ValueError as exc:
            if str(exc) == "SKILL_EXISTS":
                existing_id = proposed.get("id")
                if existing_id:
                    activate_skill(dashboard, existing_id)
                    skill_id = existing_id
                else:
                    raise
            else:
                raise
        item["status"] = "resolved"
        item["resolvedAction"] = "approve_install"
        return {"inboxId": inbox_id, "skillId": skill_id}

    try:
        result, patch = run_mutation(session, _apply, patch_domains=["inbox", "skills", "pulse"])
    except ValueError as exc:
        code = str(exc)
        if code == "INBOX_NOT_FOUND":
            raise fail("INBOX_NOT_FOUND", "收件项不存在", status=404) from exc
        if code == "INVALID_CATEGORY":
            raise fail("INVALID_CATEGORY", "非 Skill 安装提案", status=400) from exc
        if code == "MISSING_SKILL_DOC":
            raise fail("MISSING_SKILL_DOC", "提案缺少 SKILL 文档", status=400) from exc
        if code == "SKILL_EXISTS":
            raise fail("SKILL_EXISTS", "Skill 已存在", status=409) from exc
        raise fail("IMPORT_FAILED", str(exc), status=400) from exc
    return ok(result, patch=patch)
