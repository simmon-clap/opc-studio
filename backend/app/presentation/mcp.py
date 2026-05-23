"""MCP connections sync — Epic 4."""

from __future__ import annotations

from typing import Any


def sync_mcp_connections(dashboard: dict[str, Any]) -> None:
    dashboard.setdefault("mcpConnections", [])


def get_connection(dashboard: dict[str, Any], connection_id: str) -> dict[str, Any] | None:
    sync_mcp_connections(dashboard)
    return next(
        (c for c in dashboard.get("mcpConnections", []) if c.get("id") == connection_id),
        None,
    )


def allowed_mcp_for_role(dashboard: dict[str, Any], role_id: str) -> list[str]:
    sync_mcp_connections(dashboard)
    out: list[str] = []
    for conn in dashboard.get("mcpConnections", []):
        if conn.get("health") == "disabled":
            continue
        allowed = conn.get("allowedRoles") or []
        if not allowed or role_id in allowed:
            out.append(conn["id"])
    return out
