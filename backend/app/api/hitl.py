"""HITL approval endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session

from app.api.deps import fail, ok, run_mutation
from app.db import get_session
from app.services import orchestrator_hooks
from app.services.dashboard_store import get_dashboard
from app.services.state_machines import approve_hitl, reject_hitl

router = APIRouter(tags=["hitl"])


class RejectBody(BaseModel):
    note: str | None = None


@router.get("/hitl/{hitl_id}")
def get_hitl(hitl_id: str, session: Session = Depends(get_session)):
    dashboard = get_dashboard(session)
    for item in dashboard.get("hitlQueue", []):
        if item.get("id") == hitl_id:
            return ok(item)
    raise fail("HITL_NOT_FOUND", "HITL 不存在", status=404)


@router.post("/hitl/{hitl_id}/approve")
async def approve_hitl_route(hitl_id: str, session: Session = Depends(get_session)):
    def _apply(dashboard):
        return approve_hitl(dashboard, hitl_id)

    try:
        result = run_mutation(session, _apply)
    except ValueError as exc:
        code = str(exc)
        if code == "HITL_NOT_FOUND":
            raise fail("HITL_NOT_FOUND", "HITL 不存在", status=404) from exc
        if code == "HITL_ALREADY_APPROVED":
            raise fail("HITL_ALREADY_APPROVED", "该 HITL 已批准", status=409) from exc
        raise

    await orchestrator_hooks.on_hitl_approved(hitl_id, result.get("projectId"))
    return ok(result)


@router.post("/hitl/{hitl_id}/reject")
async def reject_hitl_route(
    hitl_id: str,
    body: RejectBody | None = None,
    session: Session = Depends(get_session),
):
    note = body.note if body else None

    def _apply(dashboard):
        return reject_hitl(dashboard, hitl_id, note)

    try:
        result = run_mutation(session, _apply)
    except ValueError as exc:
        code = str(exc)
        if code == "HITL_NOT_FOUND":
            raise fail("HITL_NOT_FOUND", "HITL 不存在", status=404) from exc
        if code == "HITL_ALREADY_APPROVED":
            raise fail("HITL_ALREADY_APPROVED", "该 HITL 已批准", status=409) from exc
        raise

    await orchestrator_hooks.on_hitl_rejected(hitl_id, result.get("projectId"), result.get("note", ""))
    return ok(result)


@router.get("/reject-history")
def reject_history(session: Session = Depends(get_session)):
    dashboard = get_dashboard(session)
    return ok(dashboard.get("rejectHistory", []))
