"""CEO auto-dispatch from low-risk proposals."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.agency.delivery_score import recent_delivery_score
from app.agency.proposal_actions import execute_proposal_dispatch
from app.services.runtime_settings import ceo_auto_dispatch_enabled, get_runtime_settings

RISK_RANK = {"low": 0, "medium": 1, "high": 2}


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _cooldown_ok(
    dashboard: dict[str, Any], project_id: str | None, cooldown_min: int
) -> bool:
    if not project_id:
        return True
    meta = dashboard.setdefault("meta", {})
    log = meta.setdefault("agencyAutoDispatch", {})
    last_at = _parse_iso((log.get("byProject") or {}).get(project_id))
    if not last_at:
        return True
    elapsed = (datetime.now(timezone.utc) - last_at.astimezone(timezone.utc)).total_seconds() / 60.0
    return elapsed >= cooldown_min


def _record_auto_dispatch(dashboard: dict[str, Any], project_id: str | None) -> None:
    if not project_id:
        return
    meta = dashboard.setdefault("meta", {})
    log = meta.setdefault("agencyAutoDispatch", {})
    by_project = log.setdefault("byProject", {})
    by_project[project_id] = _now_iso()


def should_auto_dispatch(
    dashboard: dict[str, Any], inbox_item: dict[str, Any]
) -> bool:
    if not ceo_auto_dispatch_enabled(dashboard):
        return False
    if inbox_item.get("category") != "proposal" or inbox_item.get("status") != "active":
        return False

    settings = get_runtime_settings(dashboard)
    cfg = settings.get("ceoAutoDispatch") or {}
    proposal = inbox_item.get("proposal") or {}

    if (proposal.get("suggestedAction") or "review") != "dispatch":
        return False

    risk = (proposal.get("riskLevel") or "low").lower()
    max_risk = (cfg.get("maxRiskLevel") or "low").lower()
    if RISK_RANK.get(risk, 99) > RISK_RANK.get(max_risk, 0):
        return False

    project_id = inbox_item.get("projectId")
    min_score = float(cfg.get("minDeliveryScore") or 80)
    score = recent_delivery_score(dashboard, project_id=project_id)
    if score > 0 and score < min_score:
        return False
    if score <= 0 and risk != "low":
        return False

    cooldown = int(cfg.get("cooldownMin") or 15)
    return _cooldown_ok(dashboard, project_id, cooldown)


def apply_auto_dispatch(dashboard: dict[str, Any]) -> dict[str, Any]:
    """Dispatch eligible proposals and mark inbox items done."""
    if not ceo_auto_dispatch_enabled(dashboard):
        return {"dispatched": 0, "skipped": 0}

    dispatched = 0
    skipped = 0
    task_ids: list[str] = []

    for item in dashboard.get("inbox") or []:
        if item.get("category") != "proposal" or item.get("status") != "active":
            continue
        if not should_auto_dispatch(dashboard, item):
            skipped += 1
            continue
        task = execute_proposal_dispatch(dashboard, item)
        if not task:
            skipped += 1
            continue
        item["status"] = "done"
        item["read"] = True
        item["resolution"] = "auto_approved"
        item["resolvedAt"] = _now_iso()
        _record_auto_dispatch(dashboard, item.get("projectId"))
        task_ids.append(task["id"])
        dispatched += 1

    return {"dispatched": dispatched, "skipped": skipped, "taskIds": task_ids}
