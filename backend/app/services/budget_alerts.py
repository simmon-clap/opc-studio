"""Budget threshold → CEO inbox escalation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def maybe_escalate_budget(dashboard: dict[str, Any]) -> bool:
    """Create inbox reminder when finance summary budgetAlert is true."""
    from app.presentation.finance import sync_finance

    sync_finance(dashboard)
    costs = dashboard.get("costs") or {}
    summary = costs.get("summary") or {}
    if not summary.get("budgetAlert"):
        return False
    inbox = dashboard.setdefault("inbox", [])
    msg = summary.get("budgetAlertMessage") or "Token 成本接近月度预算上限"
    for item in inbox:
        if item.get("category") == "reminder" and item.get("budgetAlert") and item.get("status") == "active":
            item["preview"] = msg
            item["at"] = _now_iso()
            return False
    inbox.insert(
        0,
        {
            "id": f"inbox-budget-{uuid4().hex[:8]}",
            "category": "reminder",
            "channel": "web",
            "title": "⚠️ Token 预算告警",
            "preview": msg,
            "budgetAlert": True,
            "at": _now_iso(),
            "read": False,
            "status": "active",
        },
    )
    return True
