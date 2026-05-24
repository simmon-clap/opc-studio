"""Dashboard read API."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.deps import ok
from app.db import get_session
from app.services.dashboard_store import materialize_dashboard

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
def read_dashboard(session: Session = Depends(get_session)):
    """Return dashboard with freshly derived pulse / roles / stats (read-only)."""
    return ok(materialize_dashboard(session))
