"""Dashboard JSON blob storage."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class AppState(SQLModel, table=True):
    __tablename__ = "app_state"

    key: str = Field(primary_key=True)
    value_json: str
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
