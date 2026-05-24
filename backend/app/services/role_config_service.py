"""Resolve per-role runtime LLM configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlmodel import Session

from app.models.role_secrets import RoleSecret
from app.presentation.roles_registry import migrate_role_config_models
from app.security.role_credentials import get_slot_runtime


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
    session: Session, dashboard: dict[str, Any], role_id: str, capability: str = "text"
) -> RoleRuntimeConfig:
    cfg = next(
        (c for c in dashboard.get("roleConfig", []) if c.get("roleId") == role_id),
        {},
    )
    role = next((r for r in dashboard.get("roles", []) if r.get("id") == role_id), {})
    secret = session.get(RoleSecret, role_id)

    migrate_role_config_models(cfg if isinstance(cfg, dict) else {})
    cfg_dict = cfg if isinstance(cfg, dict) else {}
    cap = capability if capability in ("text", "image", "video", "code") else "text"
    slot = (cfg_dict.get("models") or {}).get(cap) or {}
    if cap == "text" and not slot:
        slot = (cfg_dict.get("models") or {}).get("text") or {}

    cred = get_slot_runtime(secret, cap)
    api_base_url = (
        cred.get("api_base_url")
        or slot.get("apiBaseUrl")
        or cfg_dict.get("apiBaseUrl")
        or "https://openrouter.ai/api/v1"
    )
    api_key = cred.get("api_key")

    profile_doc = (
        (dashboard.get("roleProfiles") or {}).get(role_id, {}).get("document") or ""
    ).strip()

    return RoleRuntimeConfig(
        role_id=role_id,
        model=slot.get("model") or cfg_dict.get("model") or "gpt-4o-mini",
        api_provider=slot.get("apiProvider") or cfg_dict.get("apiProvider") or "OpenRouter",
        api_base_url=api_base_url.rstrip("/"),
        api_key=api_key,
        monthly_budget=int(cfg_dict.get("monthlyBudget") or 0),
        tools=list(cfg_dict.get("tools") or []),
        name=role.get("name") or role_id,
        charter=role.get("charter") or "",
        role_prompt=cfg_dict.get("rolePrompt") or profile_doc or None,
    )
