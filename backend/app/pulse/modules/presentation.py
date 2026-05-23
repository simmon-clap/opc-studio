"""Presentation / derived view refresh tick."""

from __future__ import annotations

from typing import Any

from sqlmodel import Session

from app.presentation.derived import recompute_presentation
from app.services import aggregates
from app.services.dashboard_store import mutate
from app.services.dispatch_feed import sync_dispatch_feed


def tick_presentation(session: Session) -> dict[str, Any]:
    with mutate(session) as dashboard:
        sync_dispatch_feed(dashboard)
        aggregates.recompute_pulse(dashboard)
        aggregates.recompute_stats(dashboard)
        aggregates.recompute_role_live_state(dashboard)
        recompute_presentation(dashboard)
    return {"action": "recomputed"}
