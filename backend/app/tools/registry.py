"""Built-in tool registry — Epic 2."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

ToolHandler = Callable[[dict[str, Any], "ToolExecutionContext"], Awaitable[dict[str, Any]]]


@dataclass
class ToolSpec:
    id: str
    name: str
    description: str
    parameters_schema: dict[str, Any]
    handler: ToolHandler
    roles_default: frozenset[str] | None = None


@dataclass
class ToolExecutionContext:
    dashboard: dict[str, Any]
    role_id: str
    project_id: str
    task: dict[str, Any]
    session: Any = None


@dataclass
class ToolCallRecord:
    tool_id: str
    arguments: dict[str, Any]
    result: dict[str, Any] | None = None
    error: str | None = None


_REGISTRY: dict[str, ToolSpec] = {}


def register_tool(spec: ToolSpec) -> None:
    _REGISTRY[spec.id] = spec


def get_tool(tool_id: str) -> ToolSpec | None:
    return _REGISTRY.get(tool_id)


def list_tools() -> list[ToolSpec]:
    return list(_REGISTRY.values())


def tools_openai_schema(tool_ids: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for tid in tool_ids:
        spec = _REGISTRY.get(tid)
        if not spec:
            continue
        out.append(
            {
                "type": "function",
                "function": {
                    "name": spec.id,
                    "description": spec.description,
                    "parameters": spec.parameters_schema,
                },
            }
        )
    return out


def resolve_allowed_tools(
    dashboard: dict[str, Any],
    role_id: str,
    *,
    skill_tools: list[str] | None = None,
) -> list[str]:
    """Effective tools = skill tools ∩ role policy ∩ registry."""
    from app.presentation.roles_registry import sync_role_registry

    sync_role_registry(dashboard)
    cfg = next(
        (c for c in dashboard.get("roleConfig", []) if c.get("roleId") == role_id),
        {},
    )
    policy = cfg.get("toolPolicy") or {}
    allow_extra = set(policy.get("allow") or [])
    deny = set(policy.get("deny") or [])

    if skill_tools is not None:
        candidates = [t for t in skill_tools if t in _REGISTRY]
    else:
        legacy = set(cfg.get("tools") or [])
        defaults = {
            tid
            for tid, spec in _REGISTRY.items()
            if spec.roles_default is None or role_id in (spec.roles_default or frozenset())
        }
        candidates = sorted(legacy | defaults | allow_extra)

    return [t for t in candidates if t not in deny and t in _REGISTRY]


async def execute_tool(
    tool_id: str,
    arguments: dict[str, Any],
    ctx: ToolExecutionContext,
    *,
    allowed_tools: list[str],
) -> ToolCallRecord:
    if tool_id not in allowed_tools:
        return ToolCallRecord(
            tool_id=tool_id,
            arguments=arguments,
            error=f"TOOL_NOT_ALLOWED:{tool_id}",
        )
    spec = _REGISTRY.get(tool_id)
    if spec is None:
        return ToolCallRecord(tool_id=tool_id, arguments=arguments, error="TOOL_NOT_FOUND")
    try:
        result = await spec.handler(arguments, ctx)
        return ToolCallRecord(tool_id=tool_id, arguments=arguments, result=result)
    except Exception as exc:  # noqa: BLE001 — audit trail
        return ToolCallRecord(tool_id=tool_id, arguments=arguments, error=str(exc))


def bootstrap_tools() -> None:
    if _REGISTRY:
        return
    from app.tools import handlers as h

    register_tool(
        ToolSpec(
            id="read_project_brief",
            name="读项目 Brief",
            description="读取指定项目的 brief 与阶段信息",
            parameters_schema={
                "type": "object",
                "properties": {"projectId": {"type": "string"}},
                "required": ["projectId"],
            },
            handler=h.read_project_brief,
            roles_default=frozenset({"ceo", "product", "legal", "dev", "ops"}),
        )
    )
    register_tool(
        ToolSpec(
            id="write_artifact_file",
            name="写交付物",
            description="创建或更新项目交付物 Markdown 内容",
            parameters_schema={
                "type": "object",
                "properties": {
                    "projectId": {"type": "string"},
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "kind": {"type": "string"},
                },
                "required": ["projectId", "title", "content"],
            },
            handler=h.write_artifact_file,
            roles_default=frozenset({"product", "legal", "dev", "ops"}),
        )
    )
    register_tool(
        ToolSpec(
            id="read_template",
            name="读模板",
            description="读取内置法务/交付模板骨架",
            parameters_schema={
                "type": "object",
                "properties": {"templateId": {"type": "string"}},
                "required": ["templateId"],
            },
            handler=h.read_template,
            roles_default=frozenset({"legal", "product"}),
        )
    )
    register_tool(
        ToolSpec(
            id="update_pipeline",
            name="更新 Pipeline",
            description="更新项目 pipeline 列（运营）",
            parameters_schema={
                "type": "object",
                "properties": {
                    "projectId": {"type": "string"},
                    "column": {"type": "string"},
                },
                "required": ["projectId", "column"],
            },
            handler=h.update_pipeline,
            roles_default=frozenset({"ops", "ceo"}),
        )
    )
    register_tool(
        ToolSpec(
            id="read_founder_profile",
            name="读 Founder Profile",
            description="读取 Founder 协作偏好摘要",
            parameters_schema={"type": "object", "properties": {}},
            handler=h.read_founder_profile,
            roles_default=frozenset({"ceo", "legal", "product"}),
        )
    )
    register_tool(
        ToolSpec(
            id="propose_skill_install",
            name="提案安装 Skill",
            description="CEO 向收件箱提交 Skill 安装提案",
            parameters_schema={
                "type": "object",
                "properties": {
                    "skillMarkdown": {"type": "string"},
                    "title": {"type": "string"},
                },
                "required": ["skillMarkdown", "title"],
            },
            handler=h.propose_skill_install,
            roles_default=frozenset({"ceo"}),
        )
    )
    register_tool(
        ToolSpec(
            id="dispatch_task",
            name="派活",
            description="CEO 向指定角色派发任务（受限）",
            parameters_schema={
                "type": "object",
                "properties": {
                    "roleId": {"type": "string"},
                    "projectId": {"type": "string"},
                    "title": {"type": "string"},
                    "kind": {"type": "string"},
                },
                "required": ["roleId", "projectId", "title"],
            },
            handler=h.dispatch_task,
            roles_default=frozenset({"ceo"}),
        )
    )
