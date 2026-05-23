"""Role-to-role handoff records (Phase 3)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class Handoff(SQLModel, table=True):
    __tablename__ = "handoffs"

    id: str = Field(primary_key=True)
    project_id: str
    from_role_id: str
    to_role_id: str
    task_id: Optional[str] = None
    payload_json: Optional[str] = None
    status: str = "pending"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
