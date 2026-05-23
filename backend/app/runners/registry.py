"""Run role task via LLM when configured, else stub."""

from __future__ import annotations

from uuid import uuid4

from sqlmodel import Session

from app.deliverables.kinds import resolve_deliverable, spec_for_kind
from app.deliverables.templates import build_generation_prompt, get_template
from app.deliverables.validator import validate_content
from app.runners.base import RunContext, RunResult
from app.runners.prompts import system_prompt
from app.runners.stub import RUNNERS as STUB_RUNNERS
from app.services.llm_client import LlmError, chat_completion, estimate_cost_cny
from app.services.role_config_service import RoleRuntimeConfig, get_role_runtime_config


def _project_client(ctx: RunContext) -> tuple[dict, str]:
    project = next(
        (p for p in ctx.dashboard.get("projects", []) if p.get("id") == ctx.project_id),
        {},
    )
    client = (project.get("clientName") or ctx.project_id).replace("（线索）", "")
    return project, client


def _spec_for_ctx(ctx: RunContext, brief_text: str = "") -> "DeliverableSpec":
    task = ctx.task
    return resolve_deliverable(
        task.get("roleId") or "",
        task.get("title") or "",
        directive_kind=task.get("deliverableKind"),
        brief_context=brief_text or task.get("briefContext") or "",
    )


async def run_role(
    session: Session, ctx: RunContext, *, user_prompt: str | None = None
) -> RunResult:
    role_id = ctx.task.get("roleId") or ""
    config = get_role_runtime_config(session, ctx.dashboard, role_id)
    spec = _spec_for_ctx(ctx)

    if not config.is_configured:
        stub = STUB_RUNNERS.get(role_id)
        if stub:
            result = await stub.run(ctx)
            return _enrich_result(result, ctx, spec)
        return RunResult(progress_note="无 Runner")

    project, client = _project_client(ctx)
    if user_prompt:
        prompt = user_prompt
        max_tokens = 4000
        temperature = 0.35
    else:
        prompt, max_tokens, temperature = build_generation_prompt(
            spec,
            project_id=ctx.project_id,
            client=client,
            task_title=ctx.task.get("title") or "",
            context=ctx.task.get("briefContext") or "",
            project_stage=project.get("stage") or "",
        )

    messages = [
        {"role": "system", "content": system_prompt(role_id, config.name, config.charter, config.role_prompt)},
        {"role": "user", "content": prompt},
    ]

    try:
        resp = await chat_completion(
            config, messages, max_tokens=max_tokens, temperature=temperature
        )
    except LlmError as exc:
        tpl = get_template(spec.template_id)
        content = tpl.skeleton
        quality = validate_content(spec.kind, spec.template_id, content)
        artifact_id = f"art-{spec.kind}-{uuid4().hex[:6]}"
        return RunResult(
            artifact_id=artifact_id,
            artifact_title=spec.title,
            artifact_type=spec.kind,
            artifact_kind=spec.kind,
            artifact_format=spec.format,
            artifact_viewer=spec.viewer,
            artifact_group=spec.group,
            template_id=spec.template_id,
            artifact_status=quality["status"],
            artifact_quality=quality,
            artifact_content=content,
            handoff_to="ceo",
            progress_note=(
                f"{config.name} LLM 暂不可用，已写入专业模板骨架 · {exc.message}"
            ),
            tokens_in=0,
            tokens_out=0,
            model=config.model or "fallback-template",
            cost_cny=0,
        )

    content = (resp.content or "").strip()
    if not content:
        stub = STUB_RUNNERS.get(role_id)
        if stub:
            stub_result = await stub.run(ctx)
            content = (stub_result.artifact_content or "").strip()
    if not content:
        tpl = get_template(spec.template_id)
        content = tpl.skeleton

    quality = validate_content(spec.kind, spec.template_id, content)
    artifact_id = f"art-{spec.kind}-{uuid4().hex[:6]}"

    return RunResult(
        artifact_id=artifact_id,
        artifact_title=spec.title,
        artifact_type=spec.kind,
        artifact_kind=spec.kind,
        artifact_format=spec.format,
        artifact_viewer=spec.viewer,
        artifact_group=spec.group,
        template_id=spec.template_id,
        artifact_status=quality["status"],
        artifact_quality=quality,
        artifact_content=content,
        handoff_to="ceo",
        progress_note=(
            f"{config.name} 完成 · {spec.title} · 质量 {quality['score']}/100"
            + (f" · {quality['pendingFields']} 处待填" if quality["pendingFields"] else "")
        ),
        tokens_in=resp.input_tokens,
        tokens_out=resp.output_tokens,
        model=resp.model,
        cost_cny=estimate_cost_cny(resp.input_tokens, resp.output_tokens),
    )


def _enrich_result(result: RunResult, ctx: RunContext, spec) -> RunResult:
    content = (result.artifact_content or "").strip()
    if not content and result.artifact_id:
        tpl = get_template(spec.template_id)
        content = tpl.skeleton
    quality = validate_content(spec.kind, spec.template_id, content)
    result.artifact_kind = spec.kind
    result.artifact_format = spec.format
    result.artifact_viewer = spec.viewer
    result.artifact_group = spec.group
    result.template_id = spec.template_id
    result.artifact_type = spec.kind
    result.artifact_title = result.artifact_title or spec.title
    result.artifact_status = quality["status"]
    result.artifact_quality = quality
    result.artifact_content = content
    if not result.progress_note:
        result.progress_note = f"Stub 完成 · {spec.title}"
    return result


def build_task_prompt(ctx: RunContext, brief_text: str = "") -> str:
    """Build user prompt for task execution (used by engine override paths)."""
    project, client = _project_client(ctx)
    spec = _spec_for_ctx(ctx, brief_text)
    prompt, _, _ = build_generation_prompt(
        spec,
        project_id=ctx.project_id,
        client=client,
        task_title=ctx.task.get("title") or "",
        context=brief_text or ctx.task.get("briefContext") or "",
        project_stage=project.get("stage") or "",
    )
    return prompt


def _artifact_meta(role_id: str, task_title: str) -> tuple[str, str]:
    spec = resolve_deliverable(role_id, task_title)
    return spec.title, spec.kind


def _format_thread_for_llm(thread: list, limit: int = 14) -> str:
    lines: list[str] = []
    for msg in thread[-limit:]:
        if msg.get("type") == "ack":
            continue
        who = "Founder" if msg.get("direction") == "founder_to_ceo" else "CEO"
        text = (msg.get("text") or "").strip()
        if text:
            lines.append(f"{who}: {text}")
    return "\n".join(lines) if lines else "（尚无历史）"


async def ceo_brief_reply(
    session: Session, dashboard: dict, brief_text: str, project_id: str
) -> RunResult:
    config = get_role_runtime_config(session, dashboard, "ceo")
    project = next(
        (p for p in dashboard.get("projects", []) if p.get("id") == project_id),
        {},
    )
    ctx = RunContext(
        dashboard,
        project_id,
        {"id": "brief", "roleId": "ceo", "title": "CEO 对话"},
    )

    if not config.is_configured:
        stub = STUB_RUNNERS["ceo"]
        return await stub.run(ctx)

    history = _format_thread_for_llm(dashboard.get("ceoThread", []))
    prompt = (
        f"关联项目：{project_id} · {project.get('clientName', '')}\n"
        f"当前阶段：{project.get('stage', '未知')}\n\n"
        f"最近对话：\n{history}\n\n"
        f"Founder 刚说：\n{brief_text}\n\n"
        "请用简体中文回复 Founder。\n"
        "当前是**对话模式**：可以闲聊、讨论需求；当你判断 Founder 已给出**明确派活指令**时，"
        "系统会在后台自动调度对应 Agent（你可在回复里简要确认将安排谁做什么）。\n"
        "规则：\n"
        "- 像同事聊天，**3-8 句话**；缺信息就追问。\n"
        "- 具体任务示例：法务起草 NDA、运营登记线索、产品写 PRD、开发做 PoC；"
        "完整立项需 Founder 说「立项/开工」。\n"
        "直接给 Founder 看的回复，不要 JSON。"
    )
    messages = [
        {"role": "system", "content": system_prompt("ceo", config.name, config.charter, config.role_prompt)},
        {"role": "user", "content": prompt},
    ]
    resp = await chat_completion(config, messages, max_tokens=1500)
    return RunResult(
        progress_note=resp.content[:120],
        tokens_in=resp.input_tokens,
        tokens_out=resp.output_tokens,
        model=resp.model,
        cost_cny=estimate_cost_cny(resp.input_tokens, resp.output_tokens),
        artifact_content=resp.content,
    )
