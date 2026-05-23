"""System settings API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session

from app.api.deps import ok
from app.db import get_session
from app.presentation.settings import (
    apply_system_settings_patch,
    get_system_settings,
    settings_summary,
)
from app.services.dashboard_store import get_dashboard, mutate

router = APIRouter(tags=["settings"])


class SystemSettingsPatch(BaseModel):
    orchestration: dict[str, Any] | None = None
    channels: dict[str, Any] | None = None


@router.get("/settings/summary")
def read_settings_summary(session: Session = Depends(get_session)):
    dashboard = get_dashboard(session)
    return ok(settings_summary(dashboard))


@router.get("/system/settings")
def read_system_settings(session: Session = Depends(get_session)):
    dashboard = get_dashboard(session)
    return ok(get_system_settings(dashboard))


@router.patch("/system/settings")
def patch_system_settings(body: SystemSettingsPatch, session: Session = Depends(get_session)):
    patch = body.model_dump(exclude_none=True)
    with mutate(session) as dashboard:
        merged = apply_system_settings_patch(dashboard, patch)
    return ok(merged)
