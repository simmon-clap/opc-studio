"""System settings domain sync."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.presentation.roles_registry import sync_role_registry
from app.services.runtime_settings import DEFAULT_RUNTIME_SETTINGS, get_runtime_settings


def _default_system_settings() -> dict[str, Any]:
    return {
        "orchestration": deepcopy(DEFAULT_RUNTIME_SETTINGS),
        "channels": {"feishu": {}, "wechat": {}},
    }


def sync_settings(dashboard: dict[str, Any]) -> None:
    """Merge legacy meta.runtimeSettings into systemSettings.orchestration."""
    system = dashboard.setdefault("systemSettings", _default_system_settings())
    orchestration = get_runtime_settings(dashboard)
    system["orchestration"] = orchestration
    # Keep meta.runtimeSettings in sync for legacy readers
    dashboard.setdefault("meta", {})["runtimeSettings"] = orchestration
    sync_role_registry(dashboard)
    dashboard.setdefault("skillCatalog", [])
    dashboard.setdefault("skillChains", [])
    dashboard.setdefault("mcpConnections", [])


def get_system_settings(dashboard: dict[str, Any]) -> dict[str, Any]:
    sync_settings(dashboard)
    return dashboard.get("systemSettings", _default_system_settings())


def apply_system_settings_patch(
    dashboard: dict[str, Any], patch: dict[str, Any]
) -> dict[str, Any]:
    from app.services.runtime_settings import apply_runtime_settings_patch

    sync_settings(dashboard)
    system = dashboard.setdefault("systemSettings", _default_system_settings())
    if "orchestration" in patch and patch["orchestration"] is not None:
        merged = apply_runtime_settings_patch(dashboard, patch["orchestration"])
        system["orchestration"] = merged
    if "channels" in patch and patch["channels"] is not None:
        channels = system.setdefault("channels", {})
        channels.update(patch["channels"])
    sync_settings(dashboard)
    return get_system_settings(dashboard)


def settings_summary(dashboard: dict[str, Any]) -> dict[str, Any]:
    sync_settings(dashboard)
    registry = dashboard.get("roleRegistry", {}).get("roles", [])
    configs = dashboard.get("roleConfig", [])
    skills = dashboard.get("skillCatalog", [])
    mcp = dashboard.get("mcpConnections", [])
    active_roles = [r for r in registry if r.get("status", "active") == "active"]
    configured_keys = sum(
        1
        for cfg in configs
        if (cfg.get("models") or {}).get("text", {}).get("model")
        or cfg.get("model")
    )
    return {
        "roleCount": len(active_roles),
        "configuredKeyCount": configured_keys,
        "activeSkillCount": len([s for s in skills if s.get("status") == "active"]),
        "mcpConnectionCount": len(mcp),
    }
