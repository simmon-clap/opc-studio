"""Commitments scheduler tick — overdue reminders and daily digest."""

from __future__ import annotations

from typing import Any

from sqlmodel import Session

from app.services.scheduler_service import run_scheduler_tick


def tick_commitments(session: Session) -> dict[str, Any]:
    from app.services.dashboard_store import mutate

    with mutate(session) as dashboard:
        return run_scheduler_tick(dashboard)
