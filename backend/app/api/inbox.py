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
        item = run_mutation(session, _apply)
    except ValueError as exc:
        if str(exc) == "INBOX_NOT_FOUND":
            raise fail("INBOX_NOT_FOUND", "收件项不存在", status=404) from exc
        raise
    return ok(item)


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
        item = run_mutation(session, _apply)
    except ValueError as exc:
        if str(exc) == "INBOX_NOT_FOUND":
            raise fail("INBOX_NOT_FOUND", "收件项不存在", status=404) from exc
        raise

    await orchestrator_hooks.on_inbox_resolved(inbox_id, body.action)
    return ok(item)
