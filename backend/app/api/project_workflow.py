"""Project next-steps and workroom aggregate."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.deps import fail, ok
from app.db import get_session
from app.orchestrator.engine import get_orchestrator
from app.orchestrator.workflow_engine import get_focus_and_others
from app.presentation.workroom import build_workroom_payload
from app.services.dashboard_store import get_dashboard

router = APIRouter(tags=["projects"])


@router.get("/projects/{project_id}/next-steps")
def project_next_steps(project_id: str, session: Session = Depends(get_session)):
    dashboard = get_dashboard(session)
    focus, others = get_focus_and_others(dashboard, project_id)
    return ok({"focus": focus, "others": others})


@router.get("/projects/{project_id}/workroom")
def project_workroom(project_id: str, session: Session = Depends(get_session)):
    dashboard = get_dashboard(session)
    deliberation = get_orchestrator().get_deliberation(session, project_id)
    payload = build_workroom_payload(
        dashboard, project_id, deliberation=deliberation
    )
    if not payload:
        raise fail("PROJECT_NOT_FOUND", "项目不存在", status=404)
    return ok(payload)
