"""Agent execution run records (Phase 3)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class AgentRun(SQLModel, table=True):
    __tablename__ = "agent_runs"

    id: str = Field(primary_key=True)
    role_id: str
    project_id: Optional[str] = None
    task_id: Optional[str] = None
    model: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_cny: float = 0.0
    status: str = "pending"
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    finished_at: Optional[datetime] = None
    skill_id: Optional[str] = None
    tool_calls_json: Optional[str] = None
