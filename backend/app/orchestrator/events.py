"""Orchestration event types."""

from __future__ import annotations

from typing import Any, Literal

EventType = Literal[
    "ceo.brief",
    "hitl.approved",
    "hitl.rejected",
    "inbox.resolved",
    "weekly.sent",
    "artifact.updated",
    "handoff",
    "dispatch",
    "deliberation.opened",
    "deliberation.closed",
]


def make_event(event_type: EventType, payload: dict[str, Any]) -> dict[str, Any]:
    return {"type": event_type, "payload": payload}
