"""MCP connections API."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.api.deps import fail, ok
from app.db import get_session
from app.mcp.bridge import get_mcp_bridge
from app.presentation.mcp import get_connection, sync_mcp_connections
from app.services.dashboard_store import get_dashboard, mutate

router = APIRouter(tags=["mcp"])


class McpConnectionCreate(BaseModel):
    id: str = Field(min_length=2, max_length=32)
    label: str
    transport: str = "stdio"
    command: list[str] = Field(default_factory=list)
    env: dict[str, str] | None = None
    capabilities: list[str] = Field(default_factory=lambda: ["image"])
    allowedRoles: list[str] = Field(default_factory=list)
    maxConcurrent: int = 2
    timeoutSec: int = 120


@router.get("/mcp/connections")
def list_mcp_connections(session: Session = Depends(get_session)):
    dashboard = get_dashboard(session)
    sync_mcp_connections(dashboard)
    return ok(dashboard.get("mcpConnections", []))


@router.post("/mcp/connections")
def create_mcp_connection(body: McpConnectionCreate, session: Session = Depends(get_session)):
    with mutate(session) as dashboard:
        sync_mcp_connections(dashboard)
        conns = dashboard["mcpConnections"]
        if any(c.get("id") == body.id for c in conns):
            raise fail("MCP_EXISTS", "连接 ID 已存在", status=409)
        conn = {
            **body.model_dump(),
            "health": "unknown",
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }
        conns.append(conn)
    return ok(conn)


@router.post("/mcp/connections/{connection_id}/health")
async def check_mcp_health(connection_id: str, session: Session = Depends(get_session)):
    dashboard = get_dashboard(session)
    sync_mcp_connections(dashboard)
    bridge = get_mcp_bridge()
    bridge.configure(dashboard.get("mcpConnections") or [])
    sessions = bridge.mount([connection_id])
    result = await bridge.call_tool(connection_id, "health_check", {})
    bridge.teardown()
    health = "ok" if result.get("ok") else "error"
    with mutate(session) as dash:
        target = get_connection(dash, connection_id)
        if target:
            target["health"] = health
            target["lastHealthAt"] = datetime.now(timezone.utc).isoformat()
        if health == "error":
            dash.setdefault("inbox", []).insert(
                0,
                {
                    "id": f"inbox-mcp-{connection_id}",
                    "category": "reminder",
                    "title": f"MCP 连接异常 · {connection_id}",
                    "preview": str(result.get("error") or result)[:200],
                    "status": "active",
                    "read": False,
                    "at": datetime.now(timezone.utc).isoformat(),
                },
            )
    return ok({"connectionId": connection_id, "health": health, "detail": result})
