"""Schema migration version tracking."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class SchemaVersion(SQLModel, table=True):
    __tablename__ = "schema_version"

    id: int = Field(default=1, primary_key=True)
    version: int = Field(default=1)
    applied_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
