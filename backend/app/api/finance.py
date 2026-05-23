"""Finance summary endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.deps import ok
from app.db import get_session
from app.services.dashboard_store import get_dashboard

router = APIRouter(tags=["finance"])


@router.get("/finance/summary")
def finance_summary(session: Session = Depends(get_session)):
    dashboard = get_dashboard(session)
    return ok(dashboard.get("costs", {}))


@router.get("/finance/projects")
def finance_projects(session: Session = Depends(get_session)):
    dashboard = get_dashboard(session)
    costs = dashboard.get("costs", {})
    return ok(costs.get("byProject", []))
