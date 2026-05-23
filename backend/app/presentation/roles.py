"""Canonical role registry — extend via roleRegistry API."""

from __future__ import annotations

from typing import Any

from app.presentation.roles_registry import (
    DEFAULT_REGISTRY_ENTRIES,
    sync_role_registry,
)

# Back-compat aliases
DEFAULT_ROLES: tuple[dict[str, Any], ...] = tuple(
    {
        "id": e["id"],
        "short": e.get("shortLabel", e["id"]),
        "overview": dict(e.get("overview", {})),
    }
    for e in DEFAULT_REGISTRY_ENTRIES
)

FALLBACK_LABELS = {e["id"]: e.get("shortLabel", e["id"]) for e in DEFAULT_REGISTRY_ENTRIES}


def valid_role_ids(dashboard: dict[str, Any]) -> frozenset[str]:
    from app.presentation.roles_registry import valid_role_ids as _valid

    return _valid(dashboard)


# Legacy name
VALID_ROLE_IDS = frozenset(r["id"] for r in DEFAULT_ROLES)


def role_registry(dashboard: dict[str, Any]) -> list[dict[str, Any]]:
    """Merge registry with live roles for UI."""
    sync_role_registry(dashboard)
    live_by_id = {r["id"]: r for r in dashboard.get("roles", []) if r.get("id")}
    out: list[dict[str, Any]] = []
    for entry in dashboard.get("roleRegistry", {}).get("roles", []):
        rid = entry.get("id")
        if not rid or entry.get("status") == "disabled":
            continue
        live = live_by_id.get(rid, {})
        short = entry.get("shortLabel") or FALLBACK_LABELS.get(rid, rid)
        out.append(
            {
                "id": rid,
                "name": live.get("name") or short,
                "short": short,
                "workStatus": live.get("workStatus", "idle"),
                "overview": dict(entry.get("overview") or {"x": 50, "y": 50}),
                "capabilities": list(entry.get("capabilities") or ["text"]),
                "dispatchable": entry.get("dispatchable", True),
            }
        )
    return out


def role_label(dashboard: dict[str, Any], role_id: str) -> str:
    role = next((r for r in dashboard.get("roles", []) if r.get("id") == role_id), {})
    if role.get("name"):
        return role["name"]
    entry = next(
        (r for r in dashboard.get("roleRegistry", {}).get("roles", []) if r.get("id") == role_id),
        {},
    )
    return entry.get("shortLabel") or FALLBACK_LABELS.get(role_id, role_id)
