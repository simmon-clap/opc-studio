"""Partial dashboard slices for write responses and SSE."""

from __future__ import annotations

from typing import Any

DOMAIN_KEYS: dict[str, list[str]] = {
    "pulse": ["pulse", "stats"],
    "inbox": ["inbox", "pulse"],
    "roles": ["roles", "tasks", "pulse", "presentation"],
    "finance": ["costs", "financePresentation", "pulse"],
    "costs": ["costs", "financePresentation"],
    "projects": ["projects", "presentation"],
    "presentation": ["presentation", "overviewLive", "roles", "projects"],
    "tasks": ["tasks", "roles", "pulse"],
    "ceo": ["ceoThread", "meta", "commitments"],
    "skills": ["skillCatalog", "skillChains", "meta"],
    "channels": ["channels", "systemSettings"],
}


def build_dashboard_patch(
    dashboard: dict[str, Any], domains: list[str] | None = None
) -> dict[str, Any]:
    domains = domains or ["pulse", "inbox", "roles", "projects"]
    patch: dict[str, Any] = {}
    keys: set[str] = set()
    for domain in domains:
        keys.update(DOMAIN_KEYS.get(domain, [domain]))
    for key in keys:
        if key in dashboard:
            patch[key] = dashboard[key]
    return patch
