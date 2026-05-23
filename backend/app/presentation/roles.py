"""Canonical role registry — extend here when adding agents."""

from __future__ import annotations

from typing import Any

DEFAULT_ROLES: tuple[dict[str, Any], ...] = (
    {"id": "ceo", "short": "CEO", "overview": {"x": 50, "y": 22}},
    {"id": "product", "short": "产品", "overview": {"x": 18, "y": 42}},
    {"id": "legal", "short": "法务", "overview": {"x": 82, "y": 42}},
    {"id": "dev", "short": "开发", "overview": {"x": 28, "y": 78}},
    {"id": "ops", "short": "运营", "overview": {"x": 72, "y": 78}},
)

VALID_ROLE_IDS = frozenset(r["id"] for r in DEFAULT_ROLES)

FALLBACK_LABELS = {r["id"]: r["short"] for r in DEFAULT_ROLES}


def role_registry(dashboard: dict[str, Any]) -> list[dict[str, Any]]:
    """Merge dashboard roles with layout hints for UI."""
    by_id = {r["id"]: r for r in dashboard.get("roles", []) if r.get("id")}
    out: list[dict[str, Any]] = []
    for base in DEFAULT_ROLES:
        rid = base["id"]
        live = by_id.get(rid, {})
        out.append(
            {
                "id": rid,
                "name": live.get("name") or FALLBACK_LABELS.get(rid, rid),
                "short": base["short"],
                "workStatus": live.get("workStatus", "idle"),
                "overview": dict(base["overview"]),
            }
        )
    return out


def role_label(dashboard: dict[str, Any], role_id: str) -> str:
    role = next((r for r in dashboard.get("roles", []) if r.get("id") == role_id), {})
    return role.get("name") or FALLBACK_LABELS.get(role_id, role_id)
