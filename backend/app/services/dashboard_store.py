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


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load(session: Session) -> dict[str, Any]:
    row = session.get(AppState, DASHBOARD_KEY)
    if row is None:
        raise RuntimeError("Dashboard not seeded; call seed_if_needed() first")
    return json.loads(row.value_json)


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


def get_dashboard(session: Session) -> dict[str, Any]:
    return deepcopy(load(session))


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
