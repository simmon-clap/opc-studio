"""Rule-based dispatch planning (no transitions import — avoids circular deps)."""

from __future__ import annotations

from app.orchestrator.dispatch_planner import DispatchPlan
from app.orchestrator.directives import detect_role_directives


def _transitions():
    from app.orchestrator import transitions

    return transitions


def plan_from_rules(text: str) -> DispatchPlan:
    """Keyword fallback when CEO LLM unavailable."""
    transitions = _transitions()
    if transitions.is_casual_message(text):
        return DispatchPlan(reason="招呼/闲聊")

    directives = detect_role_directives(text)
    if directives:
        return DispatchPlan(
            should_dispatch=True,
            mode="directives",
            directives=directives,
            reason="规则识别：Founder 点名角色任务",
        )

    if transitions.is_workflow_command(text):
        if transitions.is_vague_brief(text):
            return DispatchPlan(
                should_dispatch=True,
                mode="deliberation",
                reason="规则识别：立项指令但信息仍模糊",
            )
        return DispatchPlan(
            should_dispatch=True,
            mode="kickoff",
            reason="规则识别：正式立项/开工",
        )

    if transitions.is_complete_brief(text):
        return DispatchPlan(
            should_dispatch=True,
            mode="kickoff",
            reason="规则识别：Brief 信息较完整",
        )

    return DispatchPlan(reason="规则识别：继续对话，暂派活")


def plan_should_dispatch(text: str) -> bool:
    return plan_from_rules(text).should_dispatch
