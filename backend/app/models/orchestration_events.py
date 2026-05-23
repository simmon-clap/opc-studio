"""Orchestration event log (Phase 3)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class OrchestrationEvent(SQLModel, table=True):
    __tablename__ = "orchestration_events"

    id: str = Field(primary_key=True)
    event_type: str
    project_id: Optional[str] = None
    payload_json: Optional[str] = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
