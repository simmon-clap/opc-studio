"""Delivery quality scoring for auto-dispatch gates."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def recent_delivery_score(
    dashboard: dict[str, Any],
    *,
    project_id: str | None = None,
    window_days: int = 14,
) -> float:
    """Average artifact quality / CEO review score in the lookback window."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    scores: list[int] = []

    for art in dashboard.get("artifacts") or []:
        if project_id and art.get("projectId") != project_id:
            continue
        status = art.get("status") or ""
        if status not in {"approved", "review", "done"}:
            continue
        ts = _parse_iso(art.get("approvedAt") or art.get("updatedAt"))
        if ts and ts.astimezone(timezone.utc) < cutoff:
            continue
        raw = art.get("ceoReviewScore")
        if raw is None:
            raw = (art.get("quality") or {}).get("score")
        if raw is None:
            continue
        try:
            scores.append(int(raw))
        except (TypeError, ValueError):
            continue

    if not scores:
        return 0.0
    return sum(scores) / len(scores)
