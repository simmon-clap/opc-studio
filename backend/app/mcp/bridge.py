"""MCP Bridge — stdio lifecycle stub (Epic 4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class McpSession:
    connection_id: str
    status: str = "stub"
    calls: list[dict[str, Any]] = field(default_factory=list)


class McpBridge:
    """v1 stub — records calls; Epic 4.2 adds stdio spawn."""

    def __init__(self) -> None:
        self._sessions: dict[str, McpSession] = {}

    def mount(self, connection_ids: list[str]) -> dict[str, McpSession]:
        sessions: dict[str, McpSession] = {}
        for cid in connection_ids:
            sess = McpSession(connection_id=cid, status="stub_ready")
            self._sessions[cid] = sess
            sessions[cid] = sess
        return sessions

    async def call_tool(
        self,
        connection_id: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        sess = self._sessions.get(connection_id)
        if sess is None:
            return {"ok": False, "error": "MCP_NOT_MOUNTED"}
        record = {"tool": tool_name, "arguments": arguments, "result": {"stub": True}}
        sess.calls.append(record)
        if connection_id == "image_gen_local" or "image" in connection_id:
            return {
                "ok": True,
                "artifact": {
                    "type": "image",
                    "url": "/assets/brand/logo.png",
                    "caption": arguments.get("prompt", "")[:120],
                },
            }
        return {"ok": True, "content": f"stub:{tool_name}"}

    def teardown(self) -> None:
        self._sessions.clear()


_bridge = McpBridge()


def get_mcp_bridge() -> McpBridge:
    return _bridge
