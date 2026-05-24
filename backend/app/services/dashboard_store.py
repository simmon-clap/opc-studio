"""Load/save dashboard JSON in app_state."""

from __future__ import annotations

import json
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Callable, Iterator

from sqlmodel import Session, select

from app.models.app_state import AppState

DASHBOARD_KEY = "dashboard"

_cache_revision: str | None = None
_cache_snapshot: dict[str, Any] | None = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _invalidate_cache() -> None:
    global _cache_revision, _cache_snapshot
    _cache_revision = None
    _cache_snapshot = None


def _stored_revision(session: Session) -> str:
    row = session.get(AppState, DASHBOARD_KEY)
    if row is None:
        raise RuntimeError("Dashboard not seeded; call seed_if_needed() first")
    if row.updated_at is not None:
        return row.updated_at.isoformat()
    return row.value_json[:64]


def load(session: Session) -> dict[str, Any]:
    row = session.get(AppState, DASHBOARD_KEY)
    if row is None:
        raise RuntimeError("Dashboard not seeded; call seed_if_needed() first")
    return json.loads(row.value_json)


def compute_dashboard(dashboard: dict[str, Any]) -> None:
    """Recompute derived domains in-place without persisting."""
    from app.deliverables import normalize_dashboard_artifacts
    from app.services import aggregates
    from app.services.artifact_repair import repair_missing_artifacts
    from app.services.dashboard_normalize import normalize_dashboard_domains

    normalize_dashboard_domains(dashboard)
    repair_missing_artifacts(dashboard)
    normalize_dashboard_artifacts(dashboard)
    aggregates.recompute_all(dashboard)


def materialize_dashboard(session: Session) -> dict[str, Any]:
    """Load canonical JSON, compute derived fields, return an isolated copy."""
    global _cache_revision, _cache_snapshot
    rev = _stored_revision(session)
    if _cache_snapshot is not None and _cache_revision == rev:
        return deepcopy(_cache_snapshot)
    dashboard = load(session)
    compute_dashboard(dashboard)
    _cache_revision = rev
    _cache_snapshot = deepcopy(dashboard)
    return deepcopy(dashboard)


def save(session: Session, dashboard: dict[str, Any]) -> None:
    if "meta" in dashboard:
        dashboard["meta"]["updatedAt"] = _now_iso()
        dashboard["meta"]["liveBackend"] = True
    payload = json.dumps(dashboard, ensure_ascii=False)
    row = session.get(AppState, DASHBOARD_KEY)
    now = datetime.now(timezone.utc)
    if row is None:
        session.add(AppState(key=DASHBOARD_KEY, value_json=payload, updated_at=now))
    else:
        row.value_json = payload
        row.updated_at = now
        session.add(row)
    session.commit()
    _invalidate_cache()


def get_dashboard(session: Session) -> dict[str, Any]:
    return materialize_dashboard(session)


@contextmanager
def mutate(session: Session) -> Iterator[dict[str, Any]]:
    dashboard = load(session)
    yield dashboard
    save(session, dashboard)


def mutate_fn(
    session: Session,
    fn: Callable[[dict[str, Any]], dict[str, Any] | None],
) -> dict[str, Any]:
    with mutate(session) as dashboard:
        result = fn(dashboard)
        if result is not None:
            dashboard.clear()
            dashboard.update(result)
    return get_dashboard(session)


def has_dashboard(session: Session) -> bool:
    return session.get(AppState, DASHBOARD_KEY) is not None
