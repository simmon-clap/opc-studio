"""MCP Bridge — stdio subprocess with JSON-RPC fallback stub."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class McpSession:
    connection_id: str
    status: str = "stub"
    calls: list[dict[str, Any]] = field(default_factory=list)
    command: list[str] = field(default_factory=list)


class McpBridge:
    """Mount MCP connections; spawn stdio when command configured."""

    def __init__(self) -> None:
        self._sessions: dict[str, McpSession] = {}
        self._connection_cfg: dict[str, dict[str, Any]] = {}

    def configure(self, connections: list[dict[str, Any]]) -> None:
        for conn in connections:
            cid = conn.get("id")
            if cid:
                self._connection_cfg[cid] = conn

    def mount(self, connection_ids: list[str]) -> dict[str, McpSession]:
        sessions: dict[str, McpSession] = {}
        for cid in connection_ids:
            cfg = self._connection_cfg.get(cid) or {}
            cmd = cfg.get("command") or []
            sess = McpSession(
                connection_id=cid,
                status="stdio_ready" if cmd else "stub_ready",
                command=list(cmd),
            )
            self._sessions[cid] = sess
            sessions[cid] = sess
        return sessions

    async def _stdio_rpc(
        self, command: list[str], method: str, params: dict[str, Any], timeout: float = 30.0
    ) -> dict[str, Any]:
        if not command:
            return {"ok": False, "error": "NO_COMMAND"}
        req = json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
            ensure_ascii=False,
        ) + "\n"
        try:
            proc = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(
                proc.communicate(input=req.encode()),
                timeout=timeout,
            )
            line = stdout.decode(errors="replace").strip().splitlines()
            if not line:
                return {"ok": False, "error": "EMPTY_STDIO"}
            parsed = json.loads(line[-1])
            if parsed.get("error"):
                return {"ok": False, "error": parsed["error"]}
            return {"ok": True, "result": parsed.get("result")}
        except asyncio.TimeoutError:
            return {"ok": False, "error": "STDIO_TIMEOUT"}
        except (json.JSONDecodeError, OSError, FileNotFoundError) as exc:
            logger.debug("MCP stdio failed: %s", exc)
            return {"ok": False, "error": str(exc)}

    async def call_tool(
        self,
        connection_id: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        sess = self._sessions.get(connection_id)
        if sess is None:
            return {"ok": False, "error": "MCP_NOT_MOUNTED"}
        cfg = self._connection_cfg.get(connection_id) or {}
        cmd = sess.command or cfg.get("command") or []

        if tool_name == "health_check":
            if cmd:
                rpc = await self._stdio_rpc(cmd, "initialize", {"protocolVersion": "2024-11-05", "capabilities": {}})
                if rpc.get("ok"):
                    return {"ok": True, "content": "stdio ok"}
            return {"ok": True, "content": "stub ok"}

        if cmd:
            rpc = await self._stdio_rpc(
                cmd,
                "tools/call",
                {"name": tool_name, "arguments": arguments},
                timeout=float(cfg.get("timeoutSec") or 120),
            )
            if rpc.get("ok"):
                result = rpc.get("result") or {}
                content = result.get("content") if isinstance(result, dict) else result
                sess.calls.append({"tool": tool_name, "arguments": arguments, "result": result})
                return {"ok": True, "content": content}

        record = {"tool": tool_name, "arguments": arguments, "result": {"stub": True}}
        sess.calls.append(record)
        if connection_id == "image_gen_local" or "image" in connection_id:
            try:
                from app.db import session_scope
                from app.services.dashboard_store import get_dashboard
                from app.services.media_client import generate_image

                with session_scope() as session:
                    dash = get_dashboard(session)
                    role = (cfg.get("allowedRoles") or ["ceo"])[0]
                    media = await generate_image(
                        session,
                        dash,
                        role,
                        arguments.get("prompt") or "logo",
                        capability="image",
                    )
                    if media.get("url"):
                        return {"ok": True, "artifact": {"type": "image", "url": media["url"], "caption": media.get("caption")}}
            except Exception as exc:
                logger.debug("media_client fallback: %s", exc)
            return {
                "ok": True,
                "artifact": {
                    "type": "image",
                    "url": "/assets/brand/logo.png",
                    "caption": arguments.get("prompt", "")[:120],
                },
            }
        if "video" in connection_id:
            try:
                from app.db import session_scope
                from app.services.dashboard_store import get_dashboard
                from app.services.media_client import generate_video

                with session_scope() as session:
                    dash = get_dashboard(session)
                    role = (cfg.get("allowedRoles") or ["ceo"])[0]
                    media = await generate_video(
                        session,
                        dash,
                        role,
                        arguments.get("prompt") or "brand reel",
                    )
                    return {
                        "ok": True,
                        "artifact": {
                            "type": "video",
                            "url": media.get("url"),
                            "placeholder": media.get("placeholder"),
                            "caption": media.get("caption"),
                        },
                    }
            except Exception as exc:
                logger.debug("video_client fallback: %s", exc)
            return {
                "ok": True,
                "artifact": {
                    "type": "video",
                    "url": None,
                    "placeholder": True,
                    "caption": arguments.get("prompt", "")[:120],
                },
            }
        return {"ok": True, "content": f"stub:{tool_name}"}

    def teardown(self) -> None:
        self._sessions.clear()


_bridge = McpBridge()


def get_mcp_bridge() -> McpBridge:
    return _bridge
