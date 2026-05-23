"""Commitments API."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session

from app.api.deps import fail, ok, run_mutation
from app.db import get_session
from app.services.commitments import list_commitments, patch_commitment
from app.services.dashboard_store import get_dashboard

router = APIRouter(tags=["commitments"])


class CommitmentPatchBody(BaseModel):
    dueAt: str | None = None
    status: str | None = None


@router.get("/commitments")
def get_commitments(
    status: str | None = None,
    projectId: str | None = None,
    session: Session = Depends(get_session),
):
    dashboard = get_dashboard(session)
    items = list_commitments(dashboard, status=status, project_id=projectId)
    return ok(items)


@router.patch("/commitments/{commitment_id}")
def patch_commitment_route(
    commitment_id: str,
    body: CommitmentPatchBody,
    session: Session = Depends(get_session),
):
    def _apply(dashboard):
        item = patch_commitment(
            dashboard,
            commitment_id,
            due_at=body.dueAt,
            status=body.status,
        )
        if item is None:
            raise ValueError("COMMITMENT_NOT_FOUND")
        return item

    try:
        result = run_mutation(session, _apply)
    except ValueError as exc:
        if str(exc) == "COMMITMENT_NOT_FOUND":
            raise fail("COMMITMENT_NOT_FOUND", "承诺事项不存在", status=404) from exc
        raise
    return ok(result)
