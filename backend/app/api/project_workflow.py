"""Project next-steps (workflow cues)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.deps import ok
from app.db import get_session
from app.orchestrator.workflow_engine import get_next_steps
from app.services.dashboard_store import get_dashboard

router = APIRouter(tags=["projects"])


@router.get("/projects/{project_id}/next-steps")
def project_next_steps(project_id: str, session: Session = Depends(get_session)):
    dashboard = get_dashboard(session)
    steps = get_next_steps(dashboard, project_id)
    return ok(steps)
