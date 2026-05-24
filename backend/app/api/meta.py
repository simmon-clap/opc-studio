"""Meta / routing configuration API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session

from app.api.deps import ok
from app.db import get_session
from app.presentation.skills import sync_skill_catalog
from app.services.dashboard_store import get_dashboard, mutate

router = APIRouter(tags=["meta"])


class SkillRoutesPatch(BaseModel):
    skillRoutes: dict[str, str]


@router.get("/meta/skill-routes")
def get_skill_routes(session: Session = Depends(get_session)):
    dashboard = get_dashboard(session)
    sync_skill_catalog(dashboard)
    routes = (dashboard.get("meta") or {}).get("skillRoutes") or {}
    return ok(routes)


@router.patch("/meta/skill-routes")
def patch_skill_routes(body: SkillRoutesPatch, session: Session = Depends(get_session)):
    with mutate(session) as dashboard:
        sync_skill_catalog(dashboard)
        meta = dashboard.setdefault("meta", {})
        routes = meta.setdefault("skillRoutes", {})
        routes.update(body.skillRoutes)
        result = dict(routes)
    return ok(result)
