"""Founder profile and suggestion adoption."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session

from app.api.deps import fail, ok, run_mutation
from app.db import get_session
from app.services.dashboard_store import get_dashboard
from app.services.founder_profile import (
    adopt_suggestion,
    dismiss_suggestion,
    get_profile,
    update_profile,
)

router = APIRouter(tags=["founder"])


class ProfilePatchBody(BaseModel):
    document: str | None = None
    communication: dict[str, Any] | None = None
    deliverables: dict[str, Any] | None = None
    escalation: dict[str, Any] | None = None


@router.get("/founder/profile")
def read_profile(session: Session = Depends(get_session)):
    dashboard = get_dashboard(session)
    return ok(get_profile(dashboard))


@router.put("/founder/profile")
def write_profile(body: ProfilePatchBody, session: Session = Depends(get_session)):
    patch = body.model_dump(exclude_none=True)

    def _apply(dashboard):
        return update_profile(dashboard, patch)

    result, patch = run_mutation(session, _apply, patch_domains=["inbox", "pulse", "ceo"])
    return ok(result, patch=patch)


@router.post("/founder/profile/suggestions/{suggestion_id}/adopt")
def adopt_profile_suggestion(
    suggestion_id: str, session: Session = Depends(get_session)
):
    def _apply(dashboard):
        item = adopt_suggestion(dashboard, suggestion_id)
        if item is None:
            raise ValueError("SUGGESTION_NOT_FOUND")
        return item

    try:
        result, patch = run_mutation(session, _apply, patch_domains=["inbox", "pulse", "ceo"])
        return ok(result, patch=patch)
    except ValueError as exc:
        raise fail("SUGGESTION_NOT_FOUND", "建议不存在或已处理", status=404) from exc


@router.post("/founder/profile/suggestions/{suggestion_id}/dismiss")
def dismiss_profile_suggestion(
    suggestion_id: str, session: Session = Depends(get_session)
):
    def _apply(dashboard):
        item = dismiss_suggestion(dashboard, suggestion_id)
        if item is None:
            raise ValueError("SUGGESTION_NOT_FOUND")
        return item

    try:
        result, patch = run_mutation(session, _apply, patch_domains=["inbox", "pulse", "ceo"])
        return ok(result, patch=patch)
    except ValueError as exc:
        raise fail("SUGGESTION_NOT_FOUND", "建议不存在或已处理", status=404) from exc
