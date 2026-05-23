"""Deliberation turn records (Phase 3)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class DeliberationTurn(SQLModel, table=True):
    __tablename__ = "deliberation_turns"

    id: str = Field(primary_key=True)
    session_id: str = Field(foreign_key="deliberation_sessions.id")
    role_id: str
    content: str
    turn_index: int = 0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
