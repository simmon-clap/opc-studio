"""CEO unified turn — single structured reply + dispatch + commitments."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from sqlmodel import Session

from app.orchestrator.dispatch_planner import DispatchPlan, plan_dispatch
from app.orchestrator.directives import (
    RoleDirective,
    detect_context_directives,
    infer_directives_from_ceo_reply,
)
from app.orchestrator.dispatch_rules import plan_from_rules
from app.orchestrator import transitions
from app.runners.prompts import system_prompt
from app.runners.registry import _format_thread_for_llm
from app.services.founder_profile import profile_summary_for_prompt
from app.services.llm_client import LlmError, chat_completion
from app.services.ops_status import (
    is_status_query,
    summarize_active_work,
    summarize_active_work_content,
)
from app.services.project_briefs import brief_context_for_prompt, merge_brief_delta
from app.services.role_config_service import get_role_runtime_config

logger = logging.getLogger(__name__)

from app.presentation.roles_registry import dispatchable_role_ids


@dataclass
class CeoTurnResult:
    reply: str
    project_id: str
    brief_delta: dict[str, Any] = field(default_factory=dict)
    commitment_actions: list[dict[str, Any]] = field(default_factory=list)
    dispatch_plan: DispatchPlan = field(default_factory=DispatchPlan)
    profile_suggestion: dict[str, Any] | None = None
    used_llm: bool = False
    reply_content: dict[str, Any] | None = None


def _parse_turn_json(raw: str) -> dict[str, Any] | None:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


def _plan_from_turn_data(data: dict[str, Any], dashboard: dict[str, Any] | None = None) -> DispatchPlan:
    from app.presentation.roles_registry import dispatchable_role_ids

    allowed = dispatchable_role_ids(dashboard) if dashboard else frozenset()
    dispatch = data.get("dispatch") or {}
    should = bool(dispatch.get("shouldDispatch") or dispatch.get("should_dispatch"))
    mode = dispatch.get("mode") or ("directives" if should else "none")
    directives: list[RoleDirective] = []
    seen: set[str] = set()
    for item in dispatch.get("tasks") or []:
        if not isinstance(item, dict):
            continue
        role_id = (item.get("role") or item.get("role_id") or "").lower()
        if role_id not in allowed or role_id == "ceo":
            continue
        kind = (item.get("kind") or role_id).strip()
        if kind in seen:
            continue
        seen.add(kind)
        directives.append(
            RoleDirective(
                role_id=role_id,
                title=(item.get("title") or kind)[:80],
                kind=kind,
            )
        )
    if should and mode == "directives" and directives:
        return DispatchPlan(
            should_dispatch=True,
            mode="directives",
            directives=directives,
            reason="CEO Turn",
        )
    if should and mode in {"kickoff", "deliberation"}:
        return DispatchPlan(should_dispatch=True, mode=mode, reason="CEO Turn")
    return DispatchPlan(reason="CEO Turn · 继续对话")


async def run_ceo_turn(
    session: Session,
    dashboard: dict[str, Any],
    text: str,
    project_id: str,
    *,
    attachment_context: str = "",
) -> CeoTurnResult:
    project = next(
        (p for p in dashboard.get("projects", []) if p.get("id") == project_id),
        {},
    )

    if transitions.is_casual_message(text):
        return CeoTurnResult(
            reply=transitions.casual_reply_text(),
            project_id=project_id,
        )

    if is_status_query(text):
        content = summarize_active_work_content(dashboard)
        return CeoTurnResult(
            reply=content["text"],
            project_id=project_id,
            dispatch_plan=DispatchPlan(reason="状态查询"),
            reply_content=content,
        )

    config = get_role_runtime_config(session, dashboard, "ceo")
    history = _format_thread_for_llm(dashboard.get("ceoThread", []))
    brief_ctx = brief_context_for_prompt(dashboard, project_id)
    profile_ctx = profile_summary_for_prompt(dashboard)
    ops_ctx = summarize_active_work(dashboard)

    if config.is_configured:
        try:
            return await _llm_turn(
                session,
                dashboard,
                config,
                text,
                project_id,
                project,
                history,
                brief_ctx,
                profile_ctx,
                attachment_context,
                ops_ctx,
            )
        except LlmError as exc:
            logger.warning("CEO turn LLM failed, rule fallback: %s", exc.message)

    return _rule_turn(dashboard, text, project_id, attachment_context)


async def _llm_turn(
    session: Session,
    dashboard: dict[str, Any],
    config,
    text: str,
    project_id: str,
    project: dict[str, Any],
    history: str,
    brief_ctx: str,
    profile_ctx: str,
    attachment_context: str,
    ops_ctx: str,
) -> CeoTurnResult:
    allowed = dispatchable_role_ids(dashboard)
    roles_desc = "\n".join(
        f"- {r.get('id')}: {r.get('name')}"
        for r in dashboard.get("roles", [])
        if r.get("id") in allowed
    )
    prompt = (
        f"关联项目：{project_id} · {project.get('clientName', '')}\n"
        f"阶段：{project.get('stage', '未知')}\n\n"
        f"{brief_ctx}\n\n{profile_ctx}\n\n"
        f"当前任务快照（Founder 问进度/在做什么时务必据此回答）：\n{ops_ctx}\n\n"
        f"{attachment_context}\n\n"
        f"可用 Agent：\n{roles_desc}\n\n"
        f"最近对话：\n{history}\n\n"
        f"Founder 刚说：\n{text}\n\n"
        "输出 JSON（不要 markdown 包裹以外的文字）：\n"
        "{\n"
        '  "reply": "给 Founder 的自然语言回复",\n'
        f'  "projectId": "{project_id}",\n'
        '  "briefDelta": {"ndaType":"mutual","confirmedFacts":["..."]},\n'
        '  "commitments": [{"action":"open","what":"...","ownerRole":"legal","dueAt":"ISO8601"}],\n'
        '  "dispatch": {"shouldDispatch":true,"mode":"directives","tasks":[{"role":"legal","title":"...","kind":"nda"}]},\n'
        '  "profileSuggestion": {"note":"建议记住...","delta":{}} 或 null\n'
        "}\n"
        "规则：reply 与 dispatch 必须一致；追问/确认/重生成应 shouldDispatch；"
        "问进度/有哪些任务/在做什么时只总结任务快照，shouldDispatch=false；闲聊则 false。"
    )
    messages = [
        {"role": "system", "content": system_prompt("ceo", config.name, config.charter, config.role_prompt)},
        {"role": "user", "content": prompt},
    ]
    resp = await chat_completion(config, messages, max_tokens=2000, temperature=0.4)
    data = _parse_turn_json(resp.content or "")
    if not data:
        return _rule_turn(dashboard, text, project_id, attachment_context)

    reply = (data.get("reply") or "").strip() or "收到。"
    resolved_project = data.get("projectId") or project_id
    plan = _plan_from_turn_data(data, dashboard)
    if not plan.should_dispatch:
        plan = await _merge_rule_plan(session, dashboard, text, resolved_project, plan)

    return CeoTurnResult(
        reply=reply,
        project_id=resolved_project,
        brief_delta=data.get("briefDelta") or data.get("brief_delta") or {},
        commitment_actions=list(data.get("commitments") or []),
        dispatch_plan=plan,
        profile_suggestion=data.get("profileSuggestion") or data.get("profile_suggestion"),
        used_llm=True,
    )


async def _merge_rule_plan(
    session: Session,
    dashboard: dict[str, Any],
    text: str,
    project_id: str,
    current: DispatchPlan,
) -> DispatchPlan:
    ctx = detect_context_directives(text, dashboard, project_id)
    if ctx:
        return DispatchPlan(
            should_dispatch=True,
            mode="directives",
            directives=ctx,
            reason="规则兜底：上下文派活",
        )
    rule = await plan_dispatch(session, dashboard, text, project_id)
    if rule.should_dispatch:
        return rule
    return current


def _rule_turn(
    dashboard: dict[str, Any],
    text: str,
    project_id: str,
    attachment_context: str,
) -> CeoTurnResult:
    ctx_directives = detect_context_directives(text, dashboard, project_id)
    plan = plan_from_rules(text)
    if ctx_directives:
        plan = DispatchPlan(
            should_dispatch=True,
            mode="directives",
            directives=ctx_directives,
            reason="规则：上下文派活",
        )

    brief_delta: dict[str, Any] = {}
    if "双向" in text or "两边" in text:
        brief_delta["ndaType"] = "mutual"
        brief_delta["confirmedFacts"] = ["双向保密"]
    if "项目合作" in text or "项目上的合作" in text:
        brief_delta["cooperationMode"] = "project"
        brief_delta.setdefault("confirmedFacts", []).append("项目合作")

    commitments: list[dict[str, Any]] = []
    if plan.should_dispatch and plan.directives:
        for d in plan.directives:
            commitments.append(
                {
                    "action": "open",
                    "what": d.title,
                    "ownerRole": d.role_id,
                }
            )

    reply = _rule_reply(dashboard, text, plan, attachment_context)
    hinted = infer_directives_from_ceo_reply(reply, text)
    if hinted and not plan.should_dispatch:
        plan = DispatchPlan(
            should_dispatch=True,
            mode="directives",
            directives=hinted,
            reason="规则：CEO 承诺兜底",
        )
        for d in hinted:
            commitments.append({"action": "open", "what": d.title, "ownerRole": d.role_id})

    return CeoTurnResult(
        reply=reply,
        project_id=project_id,
        brief_delta=brief_delta,
        commitment_actions=commitments,
        dispatch_plan=plan,
    )


def _rule_reply(
    dashboard: dict[str, Any],
    text: str,
    plan: DispatchPlan,
    attachment_context: str,
) -> str:
    if is_status_query(text):
        base = summarize_active_work(dashboard)
    elif plan.should_dispatch and plan.directives:
        roles = "、".join(
            {"legal": "法务", "ops": "运营", "product": "产品", "dev": "开发"}.get(
                d.role_id, d.role_id
            )
            for d in plan.directives
        )
        base = f"收到。我已安排 {roles} 执行：{plan.directives[0].title}。"
    elif "没更新" in text or "重新生成" in text:
        base = "收到，我这就重新安排相关同事处理，完成后进工作室通知你。"
    else:
        base = "收到。有明确派活指令我会直接安排对应同事执行。"
    if attachment_context:
        base += "\n\n已阅读附件摘要，关键待办已纳入项目 Brief。"
    return base


def apply_turn_side_effects(
    dashboard: dict[str, Any], turn: CeoTurnResult, *, source: str
) -> None:
    merge_brief_delta(dashboard, turn.project_id, turn.brief_delta)
    from app.services.commitments import apply_commitment_actions

    apply_commitment_actions(
        dashboard,
        turn.commitment_actions,
        project_id=turn.project_id,
        source=source,
    )
    if turn.profile_suggestion and turn.profile_suggestion.get("note"):
        from app.services.founder_profile import suggest_profile_delta

        suggest_profile_delta(
            dashboard,
            note=turn.profile_suggestion["note"],
            source=source,
            delta=turn.profile_suggestion.get("delta"),
        )
