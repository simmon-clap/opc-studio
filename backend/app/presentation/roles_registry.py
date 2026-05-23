"""Dynamic role registry — bootstrap, sync, validation."""

from __future__ import annotations

import re
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

ROLE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{1,24}$")
CAPABILITIES = frozenset({"text", "image", "video", "code"})

# Bootstrap only — no brand / design mock roles.
DEFAULT_REGISTRY_ENTRIES: tuple[dict[str, Any], ...] = (
    {
        "id": "ceo",
        "kind": "agent",
        "status": "active",
        "capabilities": ["text"],
        "department": "管理层",
        "shortLabel": "CEO",
        "dispatchable": False,
        "overview": {"x": 50, "y": 22},
    },
    {
        "id": "product",
        "kind": "agent",
        "status": "active",
        "capabilities": ["text"],
        "department": "产品部",
        "shortLabel": "产品",
        "dispatchable": True,
        "overview": {"x": 18, "y": 42},
    },
    {
        "id": "legal",
        "kind": "agent",
        "status": "active",
        "capabilities": ["text"],
        "department": "财务法务部",
        "shortLabel": "法务",
        "dispatchable": True,
        "overview": {"x": 82, "y": 42},
    },
    {
        "id": "dev",
        "kind": "agent",
        "status": "active",
        "capabilities": ["text", "code"],
        "department": "研发部",
        "shortLabel": "开发",
        "dispatchable": True,
        "overview": {"x": 28, "y": 78},
    },
    {
        "id": "ops",
        "kind": "agent",
        "status": "active",
        "capabilities": ["text"],
        "department": "运营部",
        "shortLabel": "运营",
        "dispatchable": True,
        "overview": {"x": 72, "y": 78},
    },
)

DEFAULT_OVERVIEW_GRID = [
    {"x": 50, "y": 22},
    {"x": 18, "y": 42},
    {"x": 82, "y": 42},
    {"x": 28, "y": 78},
    {"x": 72, "y": 78},
    {"x": 15, "y": 58},
    {"x": 85, "y": 58},
    {"x": 40, "y": 62},
    {"x": 60, "y": 62},
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_model_slots() -> dict[str, Any]:
    return {
        "text": {
            "model": "",
            "apiProvider": "OpenRouter",
            "apiBaseUrl": "https://openrouter.ai/api/v1",
            "enabled": True,
        },
        "image": {"model": "", "apiProvider": "", "enabled": False},
        "video": {"model": "", "apiProvider": "", "enabled": False},
    }


def migrate_role_config_models(cfg: dict[str, Any]) -> None:
    """roleConfig.model → models.text (in-place)."""
    if cfg.get("models"):
        text = cfg["models"].setdefault("text", {})
        if not text.get("model") and cfg.get("model"):
            text["model"] = cfg["model"]
        if not text.get("apiProvider") and cfg.get("apiProvider"):
            text["apiProvider"] = cfg["apiProvider"]
        if not text.get("apiBaseUrl") and cfg.get("apiBaseUrl"):
            text["apiBaseUrl"] = cfg["apiBaseUrl"]
        return
    cfg["models"] = default_model_slots()
    text = cfg["models"]["text"]
    if cfg.get("model"):
        text["model"] = cfg["model"]
    if cfg.get("apiProvider"):
        text["apiProvider"] = cfg["apiProvider"]
    if cfg.get("apiBaseUrl"):
        text["apiBaseUrl"] = cfg["apiBaseUrl"]


def bootstrap_role_registry_from_defaults(dashboard: dict[str, Any]) -> None:
    registry = dashboard.setdefault("roleRegistry", {"version": 2, "roles": []})
    if registry.get("roles"):
        return
    now = _now_iso()
    registry["roles"] = [
        {**deepcopy(entry), "createdAt": now} for entry in DEFAULT_REGISTRY_ENTRIES
    ]


def _next_overview(registry_roles: list[dict[str, Any]]) -> dict[str, int]:
    used = {tuple(r.get("overview", {}).items()) for r in registry_roles if r.get("overview")}
    for slot in DEFAULT_OVERVIEW_GRID:
        key = (("x", slot["x"]), ("y", slot["y"]))
        if key not in used:
            return dict(slot)
    n = len(registry_roles)
    return {"x": 10 + (n * 11) % 80, "y": 20 + (n * 13) % 60}


def _default_live_role(entry: dict[str, Any]) -> dict[str, Any]:
    rid = entry["id"]
    return {
        "id": rid,
        "name": entry.get("shortLabel") or rid,
        "title": "",
        "department": entry.get("department") or "",
        "charter": "",
        "avatar": f"/assets/avatars/{rid}.png",
        "workStatus": "idle",
        "load": {"current": 0, "max": 2},
    }


def _default_role_config(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "roleId": entry["id"],
        "monthlyBudget": 500,
        "models": default_model_slots(),
        "enabledSkills": [],
        "toolPolicy": {"allow": [], "deny": []},
        "tools": [],
    }


def sync_role_registry(dashboard: dict[str, Any]) -> None:
    """Ensure registry, roles[], roleConfig[], roleProfiles stay aligned."""
    bootstrap_role_registry_from_defaults(dashboard)
    registry = dashboard["roleRegistry"]
    registry.setdefault("version", 2)
    entries = registry.setdefault("roles", [])

    by_id = {e["id"]: e for e in entries if e.get("id")}
    live_by_id = {r["id"]: r for r in dashboard.get("roles", []) if r.get("id")}
    cfg_by_id = {c["roleId"]: c for c in dashboard.get("roleConfig", []) if c.get("roleId")}
    profiles = dashboard.setdefault("roleProfiles", {})

    roles_out: list[dict[str, Any]] = []
    configs_out: list[dict[str, Any]] = []

    for entry in entries:
        rid = entry.get("id")
        if not rid:
            continue
        live = live_by_id.get(rid) or _default_live_role(entry)
        if rid not in live_by_id:
            roles_out.append(live)
        else:
            roles_out.append(live_by_id[rid])

        cfg = cfg_by_id.get(rid) or _default_role_config(entry)
        migrate_role_config_models(cfg)
        cfg.setdefault("enabledSkills", [])
        cfg.setdefault("toolPolicy", {"allow": [], "deny": []})
        configs_out.append(cfg)

        if rid not in profiles:
            profiles[rid] = {"document": "", "updatedAt": _now_iso()}

    dashboard["roles"] = roles_out
    dashboard["roleConfig"] = configs_out
    dashboard["roleProfiles"] = profiles

    # Drop orphan configs/profiles for removed registry entries
    valid = set(by_id)
    dashboard["roleConfig"] = [c for c in dashboard["roleConfig"] if c.get("roleId") in valid]
    dashboard["roleProfiles"] = {
        k: v for k, v in dashboard["roleProfiles"].items() if k in valid
    }


def valid_role_ids(dashboard: dict[str, Any]) -> frozenset[str]:
    sync_role_registry(dashboard)
    return frozenset(
        r["id"]
        for r in dashboard.get("roleRegistry", {}).get("roles", [])
        if r.get("id") and r.get("status", "active") != "disabled"
    )


def dispatchable_role_ids(dashboard: dict[str, Any]) -> frozenset[str]:
    sync_role_registry(dashboard)
    return frozenset(
        r["id"]
        for r in dashboard.get("roleRegistry", {}).get("roles", [])
        if r.get("id")
        and r.get("status", "active") == "active"
        and r.get("dispatchable", True)
        and r["id"] != "ceo"
    )


def registry_entry(dashboard: dict[str, Any], role_id: str) -> dict[str, Any] | None:
    sync_role_registry(dashboard)
    return next(
        (r for r in dashboard.get("roleRegistry", {}).get("roles", []) if r.get("id") == role_id),
        None,
    )


def create_registry_role(dashboard: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """Append a new role to registry and init related domains."""
    sync_role_registry(dashboard)
    role_id = payload["id"]
    if not ROLE_ID_PATTERN.match(role_id):
        raise ValueError("INVALID_ROLE_ID")
    entries = dashboard["roleRegistry"]["roles"]
    if any(e.get("id") == role_id for e in entries):
        raise ValueError("ROLE_EXISTS")

    caps = payload.get("capabilities") or ["text"]
    caps = [c for c in caps if c in CAPABILITIES] or ["text"]
    short = (payload.get("shortLabel") or payload.get("name") or role_id)[:8]
    now = _now_iso()
    entry = {
        "id": role_id,
        "kind": "agent",
        "status": "active",
        "capabilities": caps,
        "department": payload.get("department") or "",
        "shortLabel": short,
        "dispatchable": payload.get("dispatchable", True),
        "overview": _next_overview(entries),
        "createdAt": now,
    }
    entries.append(entry)

    live = _default_live_role(entry)
    live["name"] = payload.get("name") or short
    live["title"] = payload.get("title") or ""
    live["department"] = entry["department"]
    dashboard.setdefault("roles", []).append(live)

    cfg = _default_role_config(entry)
    dashboard.setdefault("roleConfig", []).append(cfg)

    dashboard.setdefault("roleProfiles", {})[role_id] = {
        "document": "",
        "updatedAt": now,
    }
    sync_role_registry(dashboard)
    return entry


def patch_registry_role(
    dashboard: dict[str, Any], role_id: str, patch: dict[str, Any]
) -> dict[str, Any] | None:
    sync_role_registry(dashboard)
    entry = registry_entry(dashboard, role_id)
    if entry is None:
        return None
    for key in ("status", "dispatchable", "capabilities", "department", "shortLabel"):
        if key in patch and patch[key] is not None:
            if key == "capabilities":
                caps = [c for c in patch[key] if c in CAPABILITIES]
                if caps:
                    entry[key] = caps
            else:
                entry[key] = patch[key]
    sync_role_registry(dashboard)
    return entry


def patch_role_identity(
    dashboard: dict[str, Any], role_id: str, patch: dict[str, Any]
) -> dict[str, Any] | None:
    sync_role_registry(dashboard)
    role = next((r for r in dashboard.get("roles", []) if r.get("id") == role_id), None)
    if role is None:
        return None
    for key in ("name", "title", "department", "charter", "avatar"):
        if key in patch and patch[key] is not None:
            role[key] = patch[key]
    return role


def registry_summary(dashboard: dict[str, Any]) -> list[dict[str, Any]]:
    """Registry merged with live identity for API."""
    sync_role_registry(dashboard)
    live_by_id = {r["id"]: r for r in dashboard.get("roles", []) if r.get("id")}
    out: list[dict[str, Any]] = []
    for entry in dashboard.get("roleRegistry", {}).get("roles", []):
        rid = entry.get("id")
        if not rid:
            continue
        live = live_by_id.get(rid, {})
        out.append(
            {
                **entry,
                "name": live.get("name") or entry.get("shortLabel") or rid,
                "title": live.get("title") or "",
                "charter": live.get("charter") or "",
                "avatar": live.get("avatar") or f"/assets/avatars/{rid}.png",
                "workStatus": live.get("workStatus", "idle"),
            }
        )
    return out
