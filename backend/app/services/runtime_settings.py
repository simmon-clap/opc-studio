"""Pulse / Agency runtime settings — stored in dashboard.meta.runtimeSettings."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

DEFAULT_RUNTIME_SETTINGS: dict[str, Any] = {
    "pulse": {
        "enabled": True,
        "executionIntervalSec": 5,
        "executionIdleIntervalSec": 60,
        "presentationIntervalSec": 2,
        "reconcileIntervalSec": 120,
        "handoffIntervalSec": 10,
        "deliveryIntervalSec": 30,
        "commitmentsIntervalSec": 3600,
        "runningStaleMin": 30,
    },
    "agency": {
        "enabled": True,
        "ceoObserveIntervalSec": 300,
        "roleObserveIntervalSec": 120,
        "projectIdleHours": 48,
        "pauseWhileCeoThreadPending": True,
        "ceoDeliberateUseLlm": False,
    },
    "ceoAutoDispatch": {
        "enabled": False,
        "minDeliveryScore": 80,
        "maxRiskLevel": "low",
        "cooldownMin": 15,
    },
    "founderNotify": {
        "openQuestionCooldownHours": 24,
        "maxProposalsPerDay": 10,
    },
}


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def get_runtime_settings(dashboard: dict[str, Any]) -> dict[str, Any]:
    stored = (dashboard.get("meta") or {}).get("runtimeSettings") or {}
    return _deep_merge(DEFAULT_RUNTIME_SETTINGS, stored)


def apply_runtime_settings_patch(
    dashboard: dict[str, Any], patch: dict[str, Any]
) -> dict[str, Any]:
    meta = dashboard.setdefault("meta", {})
    current = get_runtime_settings(dashboard)
    merged = _deep_merge(current, patch)
    meta["runtimeSettings"] = merged
    return merged


def pulse_enabled(dashboard: dict[str, Any]) -> bool:
    import os

    env = os.environ.get("OPC_PULSE_ENABLED", "1").strip().lower()
    if env in {"0", "false", "no", "off"}:
        return False
    return bool(get_runtime_settings(dashboard).get("pulse", {}).get("enabled", True))


def ceo_auto_dispatch_enabled(dashboard: dict[str, Any]) -> bool:
    cfg = get_runtime_settings(dashboard).get("ceoAutoDispatch", {})
    return bool(cfg.get("enabled"))
