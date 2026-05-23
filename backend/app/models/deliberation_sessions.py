"""CEO deliberation session records (Phase 3)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class DeliberationSession(SQLModel, table=True):
    __tablename__ = "deliberation_sessions"

    id: str = Field(primary_key=True)
    project_id: str
    topic: str
    status: str = "open"
    decision_json: Optional[str] = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    closed_at: Optional[datetime] = None
