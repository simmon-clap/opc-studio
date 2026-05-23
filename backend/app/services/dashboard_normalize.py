"""Ensure dashboard JSON has all domains for API contract compatibility."""

from __future__ import annotations

from typing import Any

from app.services.dispatch_feed import bootstrap_dispatch_feed


def normalize_dashboard_domains(dashboard: dict[str, Any]) -> None:
    dashboard.setdefault("commitments", [])
    dashboard.setdefault("projectBriefs", {})
    dashboard.setdefault("founderProfile", _default_founder_profile())
    dashboard.setdefault("profileSuggestions", [])
    dashboard.setdefault("attachments", [])
    dashboard.setdefault("dispatchFeed", [])
    meta = dashboard.setdefault("meta", {})
    meta.setdefault("lastWorkflowRun", None)
    meta.setdefault("orchestrationActive", False)
    bootstrap_dispatch_feed(dashboard)


def _default_founder_profile() -> dict[str, Any]:
    return {
        "communication": {"preferConcise": True, "maxReplySentences": 8},
        "deliverables": {
            "legal": {"preferMutualNdaTemplate": True, "rejectBulletDraft": True},
        },
        "escalation": {"alwaysHitlFor": ["contract", "sow"]},
        "learnedNotes": [],
    }
