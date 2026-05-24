"""Shared API helpers."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlmodel import Session

from app.services import aggregates
from app.services.dashboard_store import mutate


def ok(data: Any, *, patch: dict[str, Any] | None = None, **meta: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"ok": True, "data": data}
    if patch is not None:
        payload["patch"] = patch
    if meta:
        payload["meta"] = meta
    return payload


def fail(code: str, message: str, status: int = 400, **details: Any) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail={"ok": False, "error": {"code": code, "message": message, "details": details}},
    )


DEFAULT_PATCH_DOMAINS = ["pulse", "inbox", "roles", "projects"]


def run_mutation_with_patch(
    session: Session, fn, *, patch_domains: list[str] | None = None
) -> tuple[Any, dict[str, Any]]:
    from app.services.dashboard_patch import build_dashboard_patch

    domains = patch_domains or DEFAULT_PATCH_DOMAINS
    with mutate(session) as dashboard:
        result = fn(dashboard)
        aggregates.recompute_all(dashboard)
        patch = build_dashboard_patch(dashboard, domains)
    return result, patch


def run_mutation(
    session: Session,
    fn,
    *,
    patch_domains: list[str] | None = None,
) -> tuple[Any, dict[str, Any]]:
    """Run dashboard mutation and return (result, patch) for write API responses."""
    return run_mutation_with_patch(session, fn, patch_domains=patch_domains)
