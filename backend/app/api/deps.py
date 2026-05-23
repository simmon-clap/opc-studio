"""Shared API helpers."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlmodel import Session

from app.db import get_session
from app.services import aggregates
from app.services.dashboard_store import get_dashboard, mutate


def ok(data: Any, **meta: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"ok": True, "data": data}
    if meta:
        payload["meta"] = meta
    return payload


def fail(code: str, message: str, status: int = 400, **details: Any) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail={"ok": False, "error": {"code": code, "message": message, "details": details}},
    )


def run_mutation(session: Session, fn) -> dict[str, Any]:
    with mutate(session) as dashboard:
        result = fn(dashboard)
        aggregates.recompute_all(dashboard)
    return result
