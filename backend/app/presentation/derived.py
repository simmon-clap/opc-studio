"""Recompute all versioned presentation views on the dashboard."""

from __future__ import annotations

from typing import Any

from app.presentation.overview import compute_overview_live
from app.presentation.roles import role_registry
from app.presentation.schema import PRESENTATION_VERSION


def recompute_presentation(dashboard: dict[str, Any]) -> None:
    """Single entry point — call from aggregates.recompute_all."""
    overview = compute_overview_live(dashboard)
    dashboard["presentation"] = {
        "version": PRESENTATION_VERSION,
        "roles": role_registry(dashboard),
        "overview": overview,
    }
    # Compatibility alias — remove once all clients use presentation.overview
    dashboard["overviewLive"] = overview
