"""CEO dispatch planner — understand Founder intent and plan role tasks."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from sqlmodel import Session

from app.orchestrator.directives import RoleDirective, detect_context_directives, detect_role_directives
from app.runners.prompts import system_prompt
from app.runners.registry import _format_thread_for_llm
from app.services.llm_client import LlmError, chat_completion
from app.services.role_config_service import get_role_runtime_config

logger = logging.getLogger(__name__)

from app.presentation.roles_registry import DEFAULT_REGISTRY_ENTRIES, dispatchable_role_ids

# Fallback when dashboard unavailable (tests / from_dict)
_LEGACY_VALID = frozenset(r["id"] for r in DEFAULT_REGISTRY_ENTRIES)


def _transitions():
    from app.orchestrator import transitions

    return transitions


@dataclass
class DispatchPlan:
    should_dispatch: bool = False
    mode: str = "none"  # none | directives | kickoff | deliberation
    directives: list[RoleDirective] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "should_dispatch": self.should_dispatch,
            "mode": self.mode,
            "reason": self.reason,
            "directives": [
                {"role_id": d.role_id, "title": d.title, "kind": d.kind}
                for d in self.directives
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], allowed: frozenset[str] | None = None) -> "DispatchPlan":
        valid = allowed or _LEGACY_VALID
        directives = [
            RoleDirective(
                role_id=item["role_id"],
                title=item["title"],
                kind=item.get("kind", item["role_id"]),
            )
            for item in data.get("directives", [])
            if item.get("role_id") in valid and item.get("role_id") != "ceo"
        ]
        return cls(
            should_dispatch=bool(data.get("should_dispatch")),
            mode=data.get("mode") or "none",
            directives=directives,
            reason=data.get("reason") or "",
        )


from app.orchestrator.dispatch_rules import plan_from_rules as _plan_from_rules


def _parse_plan_json(raw: str) -> dict[str, Any] | None:
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


def _normalize_plan(data: dict[str, Any], dashboard: dict[str, Any] | None = None) -> DispatchPlan:
    allowed = dispatchable_role_ids(dashboard) if dashboard else _LEGACY_VALID
    mode = (data.get("mode") or "none").lower()
    if mode not in {"none", "directives", "kickoff", "deliberation"}:
        mode = "none"

    directives: list[RoleDirective] = []
    seen: set[str] = set()
    for item in data.get("tasks") or []:
        if not isinstance(item, dict):
            continue
        role_id = (item.get("role") or item.get("role_id") or "").lower()
        if role_id not in allowed or role_id == "ceo":
            continue
        title = (item.get("title") or "").strip()
        if not title:
            continue
        kind = (item.get("kind") or role_id).strip()
        if kind in seen:
            continue
        seen.add(kind)
        directives.append(RoleDirective(role_id=role_id, title=title[:80], kind=kind))

    should = bool(data.get("should_dispatch"))
    if mode == "directives" and directives:
        should = True
    elif mode in {"kickoff", "deliberation"}:
        should = True
    elif mode == "none":
        should = False
        directives = []

    if should and mode == "directives" and not directives:
        mode = "none"
        should = False

    return DispatchPlan(
        should_dispatch=should,
        mode=mode,
        directives=directives,
        reason=(data.get("reason") or "")[:200],
    )


async def plan_dispatch(
    session: Session,
    dashboard: dict[str, Any],
    text: str,
    project_id: str,
) -> DispatchPlan:
    """CEO 理解 Founder 指令 → 生成派活计划（LLM 优先，规则兜底）。"""
    transitions = _transitions()
    if transitions.is_casual_message(text):
        return DispatchPlan(reason="招呼/闲聊")

    context_directives = detect_context_directives(text, dashboard, project_id)
    if context_directives:
        return DispatchPlan(
            should_dispatch=True,
            mode="directives",
            directives=context_directives,
            reason="对话上下文：确认/追问/重生成 → 派活",
        )

    meta_hint = dashboard.get("meta", {}).get("_ceoDispatchHint")
    allowed = dispatchable_role_ids(dashboard)
    if meta_hint:
        directives = [
            RoleDirective(
                role_id=item["role_id"],
                title=item["title"],
                kind=item.get("kind", item["role_id"]),
            )
            for item in meta_hint
            if item.get("role_id") in allowed
        ]
        if directives:
            return DispatchPlan(
                should_dispatch=True,
                mode="directives",
                directives=directives,
                reason="CEO 回复已承诺派活",
            )

    config = get_role_runtime_config(session, dashboard, "ceo")
    if not config.is_configured:
        return _plan_from_rules(text)

    project = next(
        (p for p in dashboard.get("projects", []) if p.get("id") == project_id),
        {},
    )
    history = _format_thread_for_llm(dashboard.get("ceoThread", []))
    roles_desc = "\n".join(
        f"- {r.get('id')}: {r.get('name')} — {r.get('charter', '')}"
        for r in dashboard.get("roles", [])
        if r.get("id") in allowed
    )

    prompt = (
        f"关联项目：{project_id} · {project.get('clientName', '')}\n"
        f"当前阶段：{project.get('stage', '未知')}\n\n"
        f"可用 Agent（role 字段只能取 product/legal/dev/ops）：\n{roles_desc}\n\n"
        f"最近对话：\n{history}\n\n"
        f"Founder 刚说：\n{text}\n\n"
        "你是 CEO 调度器。根据**整段对话 + 本条消息**，判断 Founder 是否在**下达明确任务/指令**（而非单纯讨论、追问、补充背景）。\n"
        "若是明确指令，**动态**安排对应 Agent 执行——任务标题由你根据 Founder 原意生成，不限于固定几种模板；一条消息可派多个角色。\n\n"
        "只输出 JSON（不要 markdown 包裹以外的文字）：\n"
        "{\n"
        '  "should_dispatch": true/false,\n'
        '  "mode": "none|directives|kickoff|deliberation",\n'
        '  "tasks": [{"role":"legal|product|dev|ops","title":"任务标题","kind":"nda|prd|sow|..."}],\n'
        '  "reason": "一句话理由"\n'
        "}\n\n"
        "规则：\n"
        "- **directives**：具体派活 → tasks 中 kind 取 nda/prd/sow/quote/tech_spec/demo/acceptance/email/ops_record 等\n"
        "- **kickoff**：Founder 明确要立项/开工/走完整评估流程，且不是单一文档任务\n"
        "- **deliberation**：想推进但关键信息仍严重缺失，需多角色会诊\n"
        "- **none**：闲聊、还在对齐信息 —— 但若 Founder **确认 NDA 参数**、**追问为何没更新**、**要求重新生成**，仍应 directives 派法务\n"
        "- Founder 说「让法务写 NDA」「运营记录一下」「写好了发我」→ directives + legal/ops 任务\n"
        "- Founder 说「双向保密」「项目合作确认了」且上文在谈 NDA → directives legal kind=nda\n"
        "- Founder 说「NDA 没更新/怎么回事」→ directives legal 重新起草 nda\n"
        "- 不要派 ceo 角色；tasks 可为空数组"
    )

    messages = [
        {
            "role": "system",
            "content": system_prompt("ceo", config.name, config.charter, config.role_prompt)
            + "\n你现在输出调度 JSON，不是给 Founder 的对话正文。",
        },
        {"role": "user", "content": prompt},
    ]

    try:
        resp = await chat_completion(config, messages, max_tokens=800, temperature=0.2)
        data = _parse_plan_json(resp.content)
        if data is None:
            logger.warning("CEO dispatch plan JSON parse failed: %s", resp.content[:200])
            return _plan_from_rules(text)
        plan = _normalize_plan(data, dashboard)
        if plan.should_dispatch and plan.mode == "none" and plan.directives:
            plan.mode = "directives"
        return plan
    except LlmError as exc:
        logger.warning("CEO dispatch plan LLM failed: %s", exc.message)
        return _plan_from_rules(text)


def plan_should_dispatch(text: str) -> bool:
    from app.orchestrator.dispatch_rules import plan_should_dispatch as _psd

    return _psd(text)
