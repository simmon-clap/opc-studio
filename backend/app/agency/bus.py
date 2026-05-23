"""Proposal bus — fingerprint dedup and inbox writes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from app.agency.signals import Signal


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _active_proposal_fingerprints(dashboard: dict[str, Any]) -> set[str]:
    fps: set[str] = set()
    for item in dashboard.get("inbox", []):
        if item.get("status") != "active" or item.get("category") != "proposal":
            continue
        proposal = item.get("proposal") or {}
        fp = proposal.get("fingerprint")
        if fp:
            fps.add(fp)
    return fps


def _proposal_count_today(
    dashboard: dict[str, Any], *, from_role: str, project_id: str | None
) -> int:
    today = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
    count = 0
    for item in dashboard.get("inbox", []):
        if item.get("category") != "proposal" or item.get("status") != "active":
            continue
        if item.get("from") != from_role:
            continue
        if project_id and item.get("projectId") != project_id:
            continue
        at = (item.get("at") or "")[:10]
        if at == today:
            count += 1
    return count


def publish_signals(
    dashboard: dict[str, Any],
    signals: list[Signal],
    *,
    to_role: str = "ceo",
    daily_limit: int = 10,
) -> dict[str, Any]:
    """Write deduplicated proposal inbox entries. Returns telemetry."""
    existing = _active_proposal_fingerprints(dashboard)
    created = 0
    skipped = 0

    for signal in signals:
        fp = signal.fingerprint or f"{signal.signal_type}:{signal.project_id or 'global'}"
        if fp in existing:
            skipped += 1
            continue
        if _proposal_count_today(
            dashboard, from_role=signal.role_id, project_id=signal.project_id
        ) >= daily_limit:
            skipped += 1
            continue

        entry: dict[str, Any] = {
            "id": f"inbox-{uuid4().hex[:8]}",
            "category": "proposal",
            "from": signal.role_id,
            "to": to_role,
            "channel": "web",
            "title": signal.title or f"建议 · {signal.signal_type}",
            "preview": (signal.preview or "")[:120],
            "at": _now_iso(),
            "read": False,
            "status": "active",
            "proposal": signal.to_proposal_payload(),
        }
        if signal.project_id:
            entry["projectId"] = signal.project_id
        dashboard.setdefault("inbox", []).insert(0, entry)
        existing.add(fp)
        created += 1

    return {"created": created, "skipped": skipped, "total": len(signals)}
