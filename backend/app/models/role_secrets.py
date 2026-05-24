"""Encrypted role API credentials."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class RoleSecret(SQLModel, table=True):
    __tablename__ = "role_secrets"

    role_id: str = Field(primary_key=True)
    api_base_url: Optional[str] = None
    api_key_encrypted: Optional[str] = None
    slot_credentials_json: Optional[str] = None
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
