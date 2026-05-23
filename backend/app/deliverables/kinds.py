"""Deliverable kind registry and resolution from tasks / directives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DeliverableSpec:
    kind: str
    format: str  # markdown | code | image | link | bundle
    template_id: str
    title: str
    icon: str
    viewer: str  # contract | prd | checklist | email | memo | code | demo | markdown
    group: str  # evaluate | legal | engineering | delivery | ops


KIND_REGISTRY: dict[str, dict[str, str]] = {
    "memo": {
        "format": "markdown",
        "template_id": "ceo.memo",
        "title": "CEO 评估备忘",
        "icon": "doc",
        "viewer": "memo",
        "group": "evaluate",
    },
    "prd": {
        "format": "markdown",
        "template_id": "product.prd_agent",
        "title": "PRD 草稿",
        "icon": "doc",
        "viewer": "prd",
        "group": "legal",
    },
    "nda": {
        "format": "markdown",
        "template_id": "legal.nda_mutual_zh",
        "title": "NDA 草稿",
        "icon": "doc",
        "viewer": "contract",
        "group": "legal",
    },
    "contract": {
        "format": "markdown",
        "template_id": "legal.contract_framework",
        "title": "合同草案",
        "icon": "doc",
        "viewer": "contract",
        "group": "legal",
    },
    "sow": {
        "format": "markdown",
        "template_id": "legal.sow_fixed",
        "title": "SOW / 工作说明书",
        "icon": "doc",
        "viewer": "contract",
        "group": "legal",
    },
    "quote": {
        "format": "markdown",
        "template_id": "legal.quote",
        "title": "报价单",
        "icon": "doc",
        "viewer": "markdown",
        "group": "legal",
    },
    "tech_spec": {
        "format": "markdown",
        "template_id": "dev.tech_spec",
        "title": "技术方案",
        "icon": "doc",
        "viewer": "prd",
        "group": "engineering",
    },
    "code": {
        "format": "code",
        "template_id": "dev.code_delivery",
        "title": "代码交付说明",
        "icon": "doc",
        "viewer": "code",
        "group": "engineering",
    },
    "demo": {
        "format": "link",
        "template_id": "dev.demo",
        "title": "Demo / 交付说明",
        "icon": "link",
        "viewer": "demo",
        "group": "engineering",
    },
    "acceptance": {
        "format": "markdown",
        "template_id": "ops.acceptance",
        "title": "验收报告",
        "icon": "doc",
        "viewer": "checklist",
        "group": "delivery",
    },
    "closure": {
        "format": "markdown",
        "template_id": "ops.closure",
        "title": "结项清单",
        "icon": "doc",
        "viewer": "checklist",
        "group": "delivery",
    },
    "email": {
        "format": "markdown",
        "template_id": "ops.email",
        "title": "客户邮件草稿",
        "icon": "mail",
        "viewer": "email",
        "group": "engineering",
    },
    "ops_record": {
        "format": "markdown",
        "template_id": "ops.lead_record",
        "title": "线索台账更新",
        "icon": "doc",
        "viewer": "markdown",
        "group": "ops",
    },
    "design": {
        "format": "image",
        "template_id": "product.design",
        "title": "设计稿",
        "icon": "doc",
        "viewer": "gallery",
        "group": "engineering",
    },
    "doc": {
        "format": "markdown",
        "template_id": "generic.markdown",
        "title": "产出物",
        "icon": "doc",
        "viewer": "markdown",
        "group": "ops",
    },
}

GROUP_LABELS = {
    "evaluate": "阶段2 · 评估立项",
    "legal": "阶段3 · 方案签约",
    "engineering": "阶段4 · 开发交付",
    "delivery": "阶段5 · 验收结项",
    "ops": "运营台账",
}

# Legacy artifact.type → kind
_TYPE_TO_KIND = {
    "prd": "prd",
    "doc": "doc",
    "memo": "memo",
    "demo": "demo",
    "email": "email",
    "link": "demo",
}


def spec_for_kind(kind: str, *, task_title: str = "") -> DeliverableSpec:
    meta = KIND_REGISTRY.get(kind) or KIND_REGISTRY["doc"]
    title = task_title.split(" · ")[-1].strip() if task_title and " · " in task_title else meta["title"]
    if kind in ("nda", "sow", "quote", "contract") and not title.endswith("草稿"):
        display = meta["title"]
    else:
        display = title[:64] if title else meta["title"]
    return DeliverableSpec(
        kind=kind if kind in KIND_REGISTRY else "doc",
        format=meta["format"],
        template_id=meta["template_id"],
        title=display,
        icon=meta["icon"],
        viewer=meta["viewer"],
        group=meta["group"],
    )


def resolve_deliverable(
    role_id: str,
    task_title: str = "",
    *,
    directive_kind: str | None = None,
    brief_context: str = "",
) -> DeliverableSpec:
    if directive_kind and directive_kind in KIND_REGISTRY:
        return spec_for_kind(directive_kind, task_title=task_title)

    combined = f"{task_title} {brief_context}".lower()
    raw = f"{task_title} {brief_context}"

    if role_id == "legal":
        if any(k in combined or k in raw for k in ("nda", "保密")):
            return spec_for_kind("nda", task_title=task_title)
        if "sow" in combined or "工作说明书" in raw:
            return spec_for_kind("sow", task_title=task_title)
        if any(k in raw for k in ("报价", "quote")):
            return spec_for_kind("quote", task_title=task_title)
        if any(k in raw for k in ("合同", "contract")):
            return spec_for_kind("contract", task_title=task_title)
        return spec_for_kind("sow", task_title=task_title)

    if role_id == "product" or "prd" in combined:
        return spec_for_kind("prd", task_title=task_title)

    if role_id == "ceo":
        return spec_for_kind("memo", task_title=task_title)

    if role_id == "dev":
        if any(k in combined for k in ("poc", "demo", "演示")):
            return spec_for_kind("demo", task_title=task_title)
        if any(k in raw for k in ("代码", "脚本", "repo")):
            return spec_for_kind("code", task_title=task_title)
        return spec_for_kind("tech_spec", task_title=task_title)

    if role_id == "ops":
        if "台账" in raw or "登记" in raw or directive_kind == "ops_record":
            return spec_for_kind("ops_record", task_title=task_title)
        if any(k in raw for k in ("邮件", "email")):
            return spec_for_kind("email", task_title=task_title)
        if any(k in raw for k in ("验收", "acceptance")):
            return spec_for_kind("acceptance", task_title=task_title)
        return spec_for_kind("closure", task_title=task_title)

    return spec_for_kind("doc", task_title=task_title)


def migrate_legacy_artifact(art: dict[str, Any]) -> dict[str, Any]:
    """Add kind/format/status/viewer fields to legacy artifact records."""
    if art.get("kind"):
        return art

    legacy_type = art.get("type") or "doc"
    title = (art.get("title") or "").lower()

    if legacy_type == "doc" and ("nda" in title or "保密" in title):
        kind = "nda"
    elif legacy_type == "doc" and ("sow" in title or "报价" in title):
        kind = "quote" if "报价" in title else "sow"
    else:
        kind = _TYPE_TO_KIND.get(legacy_type, "doc")

    spec = spec_for_kind(kind, task_title=art.get("title") or "")
    art["kind"] = spec.kind
    art["format"] = spec.format
    art["viewer"] = spec.viewer
    art["group"] = spec.group
    art.setdefault("templateId", spec.template_id)
    art.setdefault("status", "draft")
    if not art.get("type"):
        art["type"] = spec.kind
    return art
