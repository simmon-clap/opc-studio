"""System settings domain sync."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.presentation.roles_registry import sync_role_registry
from app.services.runtime_settings import DEFAULT_RUNTIME_SETTINGS, get_runtime_settings


def _default_system_settings() -> dict[str, Any]:
    return {
        "orchestration": deepcopy(DEFAULT_RUNTIME_SETTINGS),
        "channels": {
            "feishu": {"appId": "", "appSecret": ""},
            "wechat": {
                "bridgeMode": "clawbot",
                "enabled": True,
                "outboundEnabled": True,
                "outboundMode": "openclaw",
                "gatewayUrl": "",
                "gatewayToken": "",
                "webhookUrl": "",
                "webhookToken": "",
                "bridgeSecret": "",
            },
        },
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


def _deep_merge_dict(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge_dict(base[key], value)
        else:
            base[key] = value
    return base


_SECRET_CHANNEL_KEYS = frozenset(
    {"gatewayToken", "webhookToken", "bridgeSecret", "appSecret", "verificationToken"}
)


def mask_channel_settings(channels: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for ch_name, cfg in (channels or {}).items():
        if not isinstance(cfg, dict):
            out[ch_name] = cfg
            continue
        masked = dict(cfg)
        for sk in _SECRET_CHANNEL_KEYS:
            if masked.get(sk):
                raw = str(masked[sk])
                masked[sk] = {"masked": f"…{raw[-4:]}" if len(raw) >= 4 else "****"}
        out[ch_name] = masked
    return out


def get_system_settings(dashboard: dict[str, Any], *, masked: bool = True) -> dict[str, Any]:
    sync_settings(dashboard)
    system = dashboard.get("systemSettings", _default_system_settings())
    if not masked:
        return system
    copy = deepcopy(system)
    if copy.get("channels"):
        copy["channels"] = mask_channel_settings(copy["channels"])
    return copy


def _merge_channel_patch(channels: dict[str, Any], patch: dict[str, Any]) -> None:
    for ch_name, ch_patch in patch.items():
        if not isinstance(ch_patch, dict):
            channels[ch_name] = ch_patch
            continue
        target = channels.setdefault(ch_name, {})
        for key, value in ch_patch.items():
            if isinstance(value, dict) and "masked" in value:
                continue
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                _deep_merge_dict(target[key], value)
            else:
                target[key] = value


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
        _merge_channel_patch(channels, patch["channels"])
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
