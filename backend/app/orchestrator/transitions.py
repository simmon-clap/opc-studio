"""Workflow transition rules (Phase 3a)."""

from __future__ import annotations

import re

from app.orchestrator.dispatch_rules import plan_should_dispatch

HITL_DISPATCH_MAP = {
    "HITL-1": ("product", "完善 PRD 并提交 HITL-1 复审"),
    "HITL-2": ("legal", "根据 PRD 出具报价与 SOW"),
    "HITL-3": ("ops", "完成结项清单与客户交付包"),
    "HITL-4": ("ops", "发送客户交付邮件并归档"),
}

# 纯招呼 / 测试 ping，不触发立项评估或会诊
CASUAL_GREETINGS = frozenset(
    {
        "halo",
        "hello",
        "hi",
        "hey",
        "yo",
        "ping",
        "test",
        "测试",
        "你好",
        "在吗",
        "在不在",
        "哈喽",
        "嗨",
        "早上好",
        "晚上好",
    }
)

BUSINESS_SIGNALS = (
    "预算",
    "范围",
    "验收",
    "交付",
    "PoC",
    "poc",
    "报价",
    "万",
    "节点",
    "客户",
    "需求",
    "项目",
    "立项",
    "合同",
    "发票",
    "审批",
    "ERP",
    "demo",
    "Demo",
)


def next_dispatch_after_hitl(hitl_type: str) -> tuple[str, str] | None:
    return HITL_DISPATCH_MAP.get(hitl_type)


def _normalize_greeting(text: str) -> str:
    t = text.strip().lower()
    t = re.sub(r"[!！?？.。,，~～]+$", "", t)
    return t


def is_casual_message(text: str) -> bool:
    """招呼、ping、极短无业务语义 → 不走立项/会诊。"""
    raw = text.strip()
    if not raw:
        return True

    norm = _normalize_greeting(raw)
    if norm in CASUAL_GREETINGS:
        return True

    # 含业务意图动词/名词 → 不是纯招呼（如「做个系统」）
    intent_markers = (
        "做",
        "想",
        "需要",
        "开发",
        "立项",
        "评估",
        "报价",
        "客户",
        "需求",
        "项目",
        "交付",
        "PoC",
        "poc",
    )
    if any(m in raw for m in intent_markers):
        return False

    if len(raw) <= 12:
        has_business = any(s.lower() in raw.lower() for s in BUSINESS_SIGNALS)
        if not has_business:
            compact = re.sub(r"\s+", "", raw)
            # 纯英文/数字短 ping
            if len(compact) <= 8 and re.fullmatch(r"[a-zA-Z0-9!?！?。.~～]+", compact):
                return True

    return False


def is_vague_brief(text: str) -> bool:
    """有业务意图但信息不足 → CEO 会诊。招呼类返回 False。"""
    if is_casual_message(text):
        return False

    t = text.strip()
    signal_count = sum(1 for s in BUSINESS_SIGNALS if s in t or s.lower() in t.lower())

    if signal_count >= 2:
        return False

    # 如「做个系统」「想做个审批流」：有意图但缺细节
    if len(t) < 80 and signal_count < 2:
        return len(t) >= 3

    if len(t) < 40:
        return signal_count < 2

    return signal_count < 2


# 明确指令：Founder 要求进入编排 / 立项 / 会诊
WORKFLOW_COMMAND_MARKERS = (
    "开工",
    "立项",
    "启动评估",
    "开始评估",
    "正式评估",
    "录入",
    "登记项目",
    "登记线索",
    "走流程",
    "派活",
    "安排会诊",
    "开个会诊",
    "开会诊",
    "开始编排",
    "可以立项",
    "信息够了",
    "开始 poc",
    "启动 poc",
    "开 poc",
    "更新 pipeline",
    "进入 pipeline",
)


def is_workflow_command(text: str) -> bool:
    t = text.strip().lower()
    return any(m.lower() in t for m in WORKFLOW_COMMAND_MARKERS)


def is_complete_brief(text: str) -> bool:
    """单条消息信息已够录入/评估（非招呼、非模糊）。"""
    if is_casual_message(text):
        return False
    return not is_vague_brief(text)


# 录入 / 登记线索
INTAKE_MARKERS = (
    "纳入",
    "记录",
    "登记",
    "录入",
    "新客户",
    "新需求",
    "记一下",
    "记下",
)


def is_intake_request(text: str) -> bool:
    return any(marker in text for marker in INTAKE_MARKERS)


def should_enter_workflow(text: str, *, intake_created: bool = False) -> bool:
    """是否进入编排（优先 CEO 调度规则；测试/兜底用）。"""
    return plan_should_dispatch(text)


def casual_reply_text() -> str:
    return (
        "在的，随便聊。你说清楚让谁做什么（如法务写 NDA、运营登记线索），"
        "我会理解后自动派活；要完整立项再说「立项」或「开工」。"
    )
