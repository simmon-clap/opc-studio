"""Parse Founder instructions into role dispatch directives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RoleDirective:
    role_id: str
    title: str
    kind: str


def _thread_context(thread: list[dict[str, Any]], limit: int = 14) -> str:
    parts: list[str] = []
    for msg in thread[-limit:]:
        if msg.get("type") == "ack":
            continue
        text = (msg.get("text") or "").strip()
        if text:
            parts.append(text)
    return "\n".join(parts)


def _nda_in_context(text: str, context: str) -> bool:
    combined = f"{text}\n{context}".lower()
    raw = f"{text}\n{context}"
    return any(
        k in combined or k in raw
        for k in ("nda", "保密协议", "保密", "nondisclosure")
    ) or "华为" in raw


def detect_role_directives(text: str) -> list[RoleDirective]:
    """Founder 点名某角色干活 → 派 Task（如法务起草 NDA）。"""
    raw = text.strip()
    if not raw:
        return []

    lower = raw.lower()
    found: list[RoleDirective] = []
    seen: set[str] = set()

    def add(role_id: str, title: str, kind: str) -> None:
        if kind in seen:
            return
        seen.add(kind)
        found.append(RoleDirective(role_id=role_id, title=title, kind=kind))

    legal_mentioned = any(m in raw for m in ("法务", "律师", "legal", "Legal"))
    nda_mentioned = any(
        m in lower or m in raw for m in ("nda", "保密协议", "保密", "nondisclosure")
    )
    legal_action = any(
        m in raw for m in ("起草", "写", "出", "准备", "开始", "给一份", "给我", "重新生成", "重写")
    )

    if nda_mentioned and (legal_mentioned or legal_action):
        add("legal", "起草 NDA", "nda")
    elif nda_mentioned and any(m in raw for m in ("写", "起草", "出", "给", "发我")):
        add("legal", "起草 NDA", "nda")

    ops_mentioned = "运营" in raw
    ops_action = any(m in raw for m in ("记录", "登记", "台账", "录入", "纳入"))
    if ops_mentioned and ops_action:
        add("ops", "更新线索台账", "ops_record")

    product_mentioned = any(m in raw for m in ("产品", "PRD", "prd"))
    product_action = any(m in raw for m in ("写", "起草", "撰写", "出"))
    if product_mentioned and product_action:
        add("product", "撰写 PRD 初稿", "prd")

    dev_mentioned = any(m in raw for m in ("开发", "工程", "dev"))
    dev_action = any(m in raw for m in ("做", "开发", "实现", "PoC", "poc", "demo"))
    if dev_mentioned and dev_action:
        add("dev", "技术方案 / Demo", "dev")

    return found


def detect_context_directives(
    text: str,
    dashboard: dict[str, Any],
    project_id: str,
) -> list[RoleDirective]:
    """从对话上下文推断待执行派活（确认参数、追问进度、重新生成等）。"""
    explicit = detect_role_directives(text)
    if explicit:
        return explicit

    raw = text.strip()
    if not raw:
        return []

    thread = dashboard.get("ceoThread", [])
    context = _thread_context(thread)
    if not _nda_in_context(raw, context):
        return []

    stale_complaint = any(
        k in raw
        for k in (
            "没更新",
            "没有更新",
            "怎么回事",
            "还没",
            "没动",
            "没出",
            "卡着",
            "什么情况",
        )
    )
    regenerate = any(
        k in raw for k in ("重新生成", "重写", "再起草", "重新起草", "专业", "再来一版")
    )
    if stale_complaint or regenerate:
        return [RoleDirective("legal", "重新起草 NDA", "nda")]

    confirms_nda = any(
        k in raw for k in ("双向", "两边", "互惠", "项目合作", "项目上的合作", "双向保密")
    )
    if confirms_nda:
        recent_ceo = _thread_context(
            [m for m in thread[-8:] if m.get("direction") == "ceo_to_founder"]
        )
        if any(
            k in recent_ceo
            for k in ("对齐", "起草", "NDA", "nda", "保密", "方向", "标准", "模板")
        ):
            title = "起草双向 NDA" if "双向" in raw or "两边" in raw else "起草 NDA"
            return [RoleDirective("legal", title, "nda")]

    return []


CEO_DISPATCH_PATTERNS = (
    "就让法务",
    "我让法务",
    "这就让法务",
    "我现在就让法务",
    "法务按",
    "法务重新",
    "法务起草",
    "安排法务",
    "法务，",
    "法务现在",
    "立刻按",
    "重拟",
)


def infer_directives_from_ceo_reply(reply: str, founder_text: str = "") -> list[RoleDirective]:
    """CEO 聊天回复里承诺派活 → 兜底调度。"""
    if not reply:
        return []
    combined = f"{reply}\n{founder_text}".lower()
    legal_dispatch = any(p in reply for p in CEO_DISPATCH_PATTERNS)
    if not legal_dispatch:
        legal_dispatch = "法务" in reply and any(
            k in reply for k in ("起草", "重拟", "NDA", "nda", "保密", "立刻")
        )
    if not legal_dispatch:
        return []
    if any(k in combined or k in reply for k in ("nda", "保密", "起草", "重拟")):
        title = "重新起草双向 NDA" if "双向" in reply else "重新起草 NDA"
        return [RoleDirective("legal", title, "nda")]
    return []
