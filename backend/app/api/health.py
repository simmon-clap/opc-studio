"""Health check endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.config import APP_VERSION

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {"ok": True, "version": APP_VERSION}
