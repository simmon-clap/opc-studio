"""Runtime settings API — Pulse / Agency configuration."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.api.deps import ok
from app.db import get_session
from app.services.dashboard_store import get_dashboard, mutate
from app.services.runtime_settings import (
    apply_runtime_settings_patch,
    get_runtime_settings,
)

router = APIRouter(tags=["runtime"])


class RuntimeSettingsPatch(BaseModel):
    pulse: dict[str, Any] | None = None
    agency: dict[str, Any] | None = None
    ceoAutoDispatch: dict[str, Any] | None = None
    founderNotify: dict[str, Any] | None = None


class CeoAutoDispatchBody(BaseModel):
    enabled: bool = Field(description="开启后 CEO 可对低危 proposal 自动派活")


@router.get("/runtime/settings")
def get_settings(session: Session = Depends(get_session)):
    dashboard = get_dashboard(session)
    return ok(get_runtime_settings(dashboard))


@router.patch("/runtime/settings")
def patch_settings(body: RuntimeSettingsPatch, session: Session = Depends(get_session)):
    patch = body.model_dump(exclude_none=True)
    with mutate(session) as dashboard:
        merged = apply_runtime_settings_patch(dashboard, patch)
    return ok(merged)


@router.post("/runtime/ceo-auto-dispatch")
def toggle_ceo_auto_dispatch(body: CeoAutoDispatchBody, session: Session = Depends(get_session)):
    with mutate(session) as dashboard:
        merged = apply_runtime_settings_patch(
            dashboard, {"ceoAutoDispatch": {"enabled": body.enabled}}
        )
    return ok(merged.get("ceoAutoDispatch", {}))
