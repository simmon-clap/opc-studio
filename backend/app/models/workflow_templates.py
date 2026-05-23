"""Workflow transition templates (Phase 3)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class WorkflowTemplate(SQLModel, table=True):
    __tablename__ = "workflow_templates"

    id: str = Field(primary_key=True)
    name: str
    project_type: Optional[str] = None
    transitions_json: str
    is_default: bool = False
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
