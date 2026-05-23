"""Dashboard read API."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.deps import ok
from app.db import get_session
from app.services import aggregates
from app.deliverables import normalize_dashboard_artifacts
from app.services.dashboard_normalize import normalize_dashboard_domains
from app.services.artifact_repair import repair_missing_artifacts
from app.services.dashboard_store import get_dashboard, mutate

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
def read_dashboard(session: Session = Depends(get_session)):
    """Return dashboard with freshly derived pulse / roles / stats."""
    with mutate(session) as dashboard:
        normalize_dashboard_domains(dashboard)
        repair_missing_artifacts(dashboard)
        normalize_dashboard_artifacts(dashboard)
        aggregates.recompute_all(dashboard)
    return ok(get_dashboard(session))
