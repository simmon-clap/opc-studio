"""Agent loop with tool enforcement — Epic 2."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from app.runners.base import RunResult
from app.services.llm_client import LlmError, chat_completion, estimate_cost_cny
from app.services.role_config_service import RoleRuntimeConfig
from app.tools.registry import (
    ToolCallRecord,
    ToolExecutionContext,
    bootstrap_tools,
    execute_tool,
    resolve_allowed_tools,
    tools_openai_schema,
)


@dataclass
class AgentLoopResult:
    content: str
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    steps: int = 0


async def run_agent_loop(
    config: RoleRuntimeConfig,
    messages: list[dict[str, Any]],
    *,
    dashboard: dict[str, Any],
    role_id: str,
    project_id: str,
    task: dict[str, Any],
    session: Any = None,
    max_steps: int = 8,
    skill_tools: list[str] | None = None,
) -> AgentLoopResult:
    bootstrap_tools()
    allowed = resolve_allowed_tools(dashboard, role_id, skill_tools=skill_tools)
    if not allowed:
        resp = await chat_completion(config, messages, max_tokens=4000)
        return AgentLoopResult(
            content=resp.content,
            input_tokens=resp.input_tokens,
            output_tokens=resp.output_tokens,
            model=resp.model,
            steps=1,
        )

    tool_ctx = ToolExecutionContext(
        dashboard=dashboard,
        role_id=role_id,
        project_id=project_id,
        task=task,
        session=session,
    )
    records: list[ToolCallRecord] = []
    total_in = 0
    total_out = 0
    model = config.model
    working = list(messages)

    for step in range(max_steps):
        # Text-only loop: parse tool calls from JSON block if model doesn't support native tools
        prompt_suffix = (
            "\n\n若需调用工具，输出 JSON："
            '{"tool":"tool_id","arguments":{...}} 或 {"final":"..."}'
            f"\n可用工具：{', '.join(allowed)}"
        )
        step_messages = working + (
            [{"role": "user", "content": prompt_suffix}] if step == 0 and len(working) == 2 else []
        )
        try:
            resp = await chat_completion(config, step_messages, max_tokens=4000, temperature=0.3)
        except LlmError:
            break
        total_in += resp.input_tokens
        total_out += resp.output_tokens
        model = resp.model
        text = resp.content.strip()

        parsed = _parse_tool_or_final(text)
        if parsed.get("final"):
            return AgentLoopResult(
                content=parsed["final"],
                tool_calls=records,
                input_tokens=total_in,
                output_tokens=total_out,
                model=model,
                steps=step + 1,
            )

        tool_id = parsed.get("tool")
        if not tool_id:
            return AgentLoopResult(
                content=text,
                tool_calls=records,
                input_tokens=total_in,
                output_tokens=total_out,
                model=model,
                steps=step + 1,
            )

        rec = await execute_tool(
            tool_id,
            parsed.get("arguments") or {},
            tool_ctx,
            allowed_tools=allowed,
        )
        records.append(rec)
        working.append({"role": "assistant", "content": text})
        working.append(
            {
                "role": "user",
                "content": f"工具 {tool_id} 结果：{json.dumps(rec.result or {'error': rec.error}, ensure_ascii=False)[:2000]}",
            }
        )

    return AgentLoopResult(
        content=records[-1].result.get("content", "") if records and records[-1].result else "",
        tool_calls=records,
        input_tokens=total_in,
        output_tokens=total_out,
        model=model,
        steps=max_steps,
    )


def _parse_tool_or_final(text: str) -> dict[str, Any]:
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            if "final" in data:
                return {"final": data["final"]}
            if "tool" in data:
                return {"tool": data["tool"], "arguments": data.get("arguments") or {}}
    except json.JSONDecodeError:
        pass
    if '"tool"' in text or '"final"' in text:
        import re

        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                data = json.loads(match.group(0))
                if isinstance(data, dict):
                    if "final" in data:
                        return {"final": data["final"]}
                    if "tool" in data:
                        return {"tool": data["tool"], "arguments": data.get("arguments") or {}}
            except json.JSONDecodeError:
                pass
    return {"final": text}


def tool_calls_to_json(records: list[ToolCallRecord]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for rec in records:
        out.append(
            {
                "toolId": rec.tool_id,
                "arguments": rec.arguments,
                "result": rec.result,
                "error": rec.error,
            }
        )
    return out
