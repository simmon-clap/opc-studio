"""Structured signals and proposals for Agency layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Signal:
    signal_type: str
    role_id: str
    project_id: str | None
    priority: str = "medium"
    title: str = ""
    preview: str = ""
    fingerprint: str = ""
    risk_level: str = "low"
    suggested_action: str = "review"
    suggested_role: str | None = None
    suggested_title: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_proposal_payload(self) -> dict[str, Any]:
        return {
            "signalType": self.signal_type,
            "fingerprint": self.fingerprint,
            "priority": self.priority,
            "riskLevel": self.risk_level,
            "suggestedAction": self.suggested_action,
            "suggestedRole": self.suggested_role,
            "suggestedTitle": self.suggested_title,
            **self.extra,
        }
