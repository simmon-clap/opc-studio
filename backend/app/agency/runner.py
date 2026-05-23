"""Agency tick — observe all roles and publish proposals."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session

from app.agency.bus import publish_signals
from app.agency.modules.roles import ROLE_OBSERVERS
from app.services.dashboard_store import get_dashboard, mutate
from app.services.runtime_settings import get_runtime_settings


def agency_enabled(dashboard: dict[str, Any]) -> bool:
    return bool(get_runtime_settings(dashboard).get("agency", {}).get("enabled", False))


def should_pause_agency(dashboard: dict[str, Any]) -> bool:
    settings = get_runtime_settings(dashboard)
    agency_cfg = settings.get("agency", {})
    meta = dashboard.get("meta") or {}

    if meta.get("orchestrationActive"):
        return True
    if not agency_cfg.get("pauseWhileCeoThreadPending", True):
        return False

    thread = dashboard.get("ceoThread") or []
    if not thread:
        return False
    last = thread[-1]
    return last.get("direction") == "ceo_to_founder" and last.get("type") == "ack"


def tick_agency(session: Session, *, role_id: str | None = None) -> dict[str, Any]:
    dashboard = get_dashboard(session)
    if not agency_enabled(dashboard):
        return {"action": "disabled"}
    if should_pause_agency(dashboard):
        return {"action": "paused"}

    settings = get_runtime_settings(dashboard)
    pulse_cfg = settings.get("pulse", {})
    stale_min = int(pulse_cfg.get("runningStaleMin") or 30)
    founder_cfg = settings.get("founderNotify", {})
    daily_limit = int(founder_cfg.get("maxProposalsPerDay") or 10)

    roles = [role_id] if role_id else list(ROLE_OBSERVERS.keys())
    telemetry: dict[str, Any] = {"roles": {}, "created": 0, "skipped": 0}

    with mutate(session) as dashboard:
        for rid in roles:
            observer = ROLE_OBSERVERS.get(rid)
            if not observer:
                continue
            if rid == "ceo":
                signals = observer(dashboard, stale_min=stale_min)
            else:
                signals = observer(dashboard)
            result = publish_signals(
                dashboard,
                signals,
                to_role="ceo",
                daily_limit=daily_limit if rid == "ceo" else min(daily_limit, 2),
            )
            telemetry["roles"][rid] = {
                "signals": len(signals),
                **result,
            }
            telemetry["created"] += result.get("created", 0)
            telemetry["skipped"] += result.get("skipped", 0)

        meta = dashboard.setdefault("meta", {})
        runtime = meta.setdefault("pulseRuntime", {})
        agency_rt = runtime.setdefault("agency", {})
        agency_rt["lastObserveAt"] = datetime.now(timezone.utc).astimezone().isoformat(
            timespec="seconds"
        )
        agency_rt["lastResult"] = telemetry

    return telemetry
