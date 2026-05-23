"""Resolve per-role runtime LLM configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlmodel import Session

from app.models.role_secrets import RoleSecret
from app.security.secrets import decrypt


@dataclass
class RoleRuntimeConfig:
    role_id: str
    model: str
    api_provider: str
    api_base_url: str
    api_key: str | None
    monthly_budget: int
    tools: list[str]
    name: str
    charter: str
    role_prompt: str | None = None

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_base_url and self.model)


def get_role_runtime_config(
    session: Session, dashboard: dict[str, Any], role_id: str
) -> RoleRuntimeConfig:
    cfg = next(
        (c for c in dashboard.get("roleConfig", []) if c.get("roleId") == role_id),
        {},
    )
    role = next((r for r in dashboard.get("roles", []) if r.get("id") == role_id), {})
    secret = session.get(RoleSecret, role_id)

    api_key = None
    api_base_url = cfg.get("apiBaseUrl") or "https://openrouter.ai/api/v1"
    if secret:
        if secret.api_base_url:
            api_base_url = secret.api_base_url
        if secret.api_key_encrypted:
            api_key = decrypt(secret.api_key_encrypted)

    return RoleRuntimeConfig(
        role_id=role_id,
        model=cfg.get("model") or "gpt-4o-mini",
        api_provider=cfg.get("apiProvider") or "OpenRouter",
        api_base_url=api_base_url.rstrip("/"),
        api_key=api_key,
        monthly_budget=int(cfg.get("monthlyBudget") or 0),
        tools=list(cfg.get("tools") or []),
        name=role.get("name") or role_id,
        charter=role.get("charter") or "",
        role_prompt=cfg.get("rolePrompt") or None,
    )
