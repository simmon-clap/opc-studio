"""Skill catalog sync, import, routing — Epic 3."""

from __future__ import annotations

import re
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

BUILTIN_SKILLS: tuple[dict[str, Any], ...] = (
    {
        "id": "nda_review_v2",
        "name": "NDA 审阅",
        "version": "2.0.0",
        "status": "active",
        "category": "legal",
        "maintainer": "builtin",
        "description": "对照 Founder 法务偏好审阅 NDA 草稿",
        "requiredCapabilities": ["text"],
        "tools": ["read_template", "write_artifact_file", "read_founder_profile"],
        "mcp": [],
        "promptTemplate": "builtin:nda_review",
        "maxSteps": 8,
        "riskLevel": "low",
    },
    {
        "id": "poc_scaffold_v1",
        "name": "PoC 脚手架",
        "version": "1.0.0",
        "status": "active",
        "category": "dev",
        "maintainer": "builtin",
        "description": "为项目生成 PoC 代码结构与 README",
        "requiredCapabilities": ["text", "code"],
        "tools": ["read_project_brief", "write_artifact_file"],
        "mcp": [],
        "promptTemplate": "builtin:poc_scaffold",
        "maxSteps": 10,
        "riskLevel": "low",
    },
    {
        "id": "weekly_compose_v1",
        "name": "周报撰写",
        "version": "1.0.0",
        "status": "active",
        "category": "ceo",
        "maintainer": "builtin",
        "description": "汇总项目进展生成 CEO 周报",
        "requiredCapabilities": ["text"],
        "tools": ["read_project_brief", "read_founder_profile"],
        "mcp": [],
        "promptTemplate": "builtin:weekly_compose",
        "maxSteps": 6,
        "riskLevel": "low",
    },
    {
        "id": "general_product",
        "name": "产品通用",
        "version": "1.0.0",
        "status": "active",
        "category": "product",
        "maintainer": "builtin",
        "description": "产品角色默认交付 Skill",
        "requiredCapabilities": ["text"],
        "tools": ["read_project_brief", "write_artifact_file"],
        "mcp": [],
        "promptTemplate": "builtin:general",
        "maxSteps": 8,
        "riskLevel": "low",
    },
    {
        "id": "general_legal",
        "name": "法务通用",
        "version": "1.0.0",
        "status": "active",
        "category": "legal",
        "maintainer": "builtin",
        "description": "法务角色默认交付 Skill",
        "requiredCapabilities": ["text"],
        "tools": ["read_template", "write_artifact_file", "read_founder_profile"],
        "mcp": [],
        "promptTemplate": "builtin:general",
        "maxSteps": 8,
        "riskLevel": "low",
    },
    {
        "id": "general_dev",
        "name": "开发通用",
        "version": "1.0.0",
        "status": "active",
        "category": "dev",
        "maintainer": "builtin",
        "description": "开发角色默认交付 Skill",
        "requiredCapabilities": ["text", "code"],
        "tools": ["read_project_brief", "write_artifact_file"],
        "mcp": [],
        "promptTemplate": "builtin:general",
        "maxSteps": 10,
        "riskLevel": "low",
    },
    {
        "id": "general_ops",
        "name": "运营通用",
        "version": "1.0.0",
        "status": "active",
        "category": "ops",
        "maintainer": "builtin",
        "description": "运营角色默认 Pipeline / 台账 Skill",
        "requiredCapabilities": ["text"],
        "tools": ["update_pipeline", "write_artifact_file"],
        "mcp": [],
        "promptTemplate": "builtin:general",
        "maxSteps": 6,
        "riskLevel": "low",
    },
    {
        "id": "general_ceo",
        "name": "CEO 通用",
        "version": "1.0.0",
        "status": "active",
        "category": "ceo",
        "maintainer": "builtin",
        "description": "CEO 评估与协调",
        "requiredCapabilities": ["text"],
        "tools": ["read_project_brief", "read_founder_profile", "dispatch_task", "propose_skill_install"],
        "mcp": [],
        "promptTemplate": "builtin:general",
        "maxSteps": 8,
        "riskLevel": "low",
    },
)

DEFAULT_SKILL_ROUTES: dict[str, str] = {
    "legal.nda_review": "nda_review_v2",
    "dev.poc_scaffold": "poc_scaffold_v1",
    "ceo.weekly_compose": "weekly_compose_v1",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sync_skill_catalog(dashboard: dict[str, Any]) -> None:
    catalog = dashboard.setdefault("skillCatalog", [])
    if not catalog:
        now = _now_iso()
        catalog.extend({**deepcopy(s), "installedAt": now} for s in BUILTIN_SKILLS)
    else:
        builtin_ids = {s["id"] for s in BUILTIN_SKILLS}
        existing = {s.get("id") for s in catalog if s.get("id")}
        for skill in BUILTIN_SKILLS:
            if skill["id"] not in existing:
                catalog.append({**deepcopy(skill), "installedAt": _now_iso()})

    dashboard.setdefault("skillChains", [])
    meta = dashboard.setdefault("meta", {})
    routes = meta.setdefault("skillRoutes", {})
    for k, v in DEFAULT_SKILL_ROUTES.items():
        routes.setdefault(k, v)


def get_skill(dashboard: dict[str, Any], skill_id: str) -> dict[str, Any] | None:
    sync_skill_catalog(dashboard)
    return next((s for s in dashboard.get("skillCatalog", []) if s.get("id") == skill_id), None)


def _parse_frontmatter(raw: str) -> dict[str, Any]:
    front: dict[str, Any] = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip()
        val = val.strip()
        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            front[key] = [x.strip().strip("'\"") for x in inner.split(",") if x.strip()] if inner else []
        else:
            front[key] = val.strip("'\"")
    return front


def parse_skill_markdown(markdown: str) -> dict[str, Any]:
    """Parse SKILL.md subset — frontmatter + body."""
    text = markdown.strip()
    front: dict[str, Any] = {}
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            front = _parse_frontmatter(parts[1])
            body = parts[2].strip()
    if not isinstance(front, dict):
        raise ValueError("INVALID_FRONTMATTER")
    skill_id = front.get("id")
    if not skill_id or not re.match(r"^[a-z][a-z0-9_-]{1,48}$", skill_id):
        raise ValueError("INVALID_SKILL_ID")
    caps = front.get("requiredCapabilities") or front.get("capabilities") or ["text"]
    if isinstance(caps, str):
        caps = [caps]
    tools = front.get("tools") or []
    if isinstance(tools, str):
        tools = [tools]
    mcp = front.get("mcp") or []
    if isinstance(mcp, str):
        mcp = [mcp]
    return {
        "id": skill_id,
        "name": front.get("name") or skill_id,
        "version": str(front.get("version") or "1.0.0"),
        "status": "draft",
        "category": front.get("category") or "custom",
        "maintainer": front.get("maintainer") or "imported",
        "description": (body.split("\n")[0] or front.get("description") or "")[:500],
        "requiredCapabilities": list(caps),
        "tools": list(tools),
        "mcp": list(mcp),
        "promptTemplate": f"inline:{skill_id}",
        "promptBody": body[:12000],
        "maxSteps": int(front.get("maxSteps") or 8),
        "riskLevel": front.get("riskLevel") or "medium",
        "installedAt": _now_iso(),
    }


def import_skill(dashboard: dict[str, Any], markdown: str) -> dict[str, Any]:
    sync_skill_catalog(dashboard)
    skill = parse_skill_markdown(markdown)
    builtin_ids = {s["id"] for s in BUILTIN_SKILLS}
    if skill["id"] in builtin_ids:
        raise ValueError("BUILTIN_PROTECTED")
    catalog = dashboard["skillCatalog"]
    if any(s.get("id") == skill["id"] for s in catalog):
        raise ValueError("SKILL_EXISTS")
    from app.tools.registry import bootstrap_tools, get_tool

    bootstrap_tools()
    for tid in skill.get("tools") or []:
        if get_tool(tid) is None:
            raise ValueError(f"UNKNOWN_TOOL:{tid}")
    catalog.append(skill)
    return skill


def activate_skill(dashboard: dict[str, Any], skill_id: str) -> dict[str, Any] | None:
    skill = get_skill(dashboard, skill_id)
    if skill is None:
        return None
    skill["status"] = "active"
    return skill


def get_chain(dashboard: dict[str, Any], chain_id: str) -> dict[str, Any] | None:
    sync_skill_catalog(dashboard)
    return next(
        (c for c in dashboard.get("skillChains", []) if c.get("id") == chain_id),
        None,
    )


def route_skill(
    dashboard: dict[str, Any],
    *,
    role_id: str,
    task_kind: str,
    skill_id: str | None = None,
    skill_chain_id: str | None = None,
) -> dict[str, Any] | None:
    """Resolve skill for a task — v1 single skill."""
    sync_skill_catalog(dashboard)
    cfg = next(
        (c for c in dashboard.get("roleConfig", []) if c.get("roleId") == role_id),
        {},
    )
    enabled = set(cfg.get("enabledSkills") or [])

    def _allowed(sid: str) -> bool:
        skill = get_skill(dashboard, sid)
        if skill is None or skill.get("status") != "active":
            return False
        return not enabled or sid in enabled

    if skill_chain_id:
        chain = get_chain(dashboard, skill_chain_id)
        if chain and chain.get("steps"):
            first_id = chain["steps"][0].get("skillId")
            if first_id and _allowed(first_id):
                return get_skill(dashboard, first_id)
        return None

    if skill_id and _allowed(skill_id):
        return get_skill(dashboard, skill_id)

    routes = (dashboard.get("meta") or {}).get("skillRoutes") or {}
    routed = routes.get(task_kind)
    if routed and _allowed(routed):
        return get_skill(dashboard, routed)

    default_id = f"general_{role_id}"
    if _allowed(default_id):
        return get_skill(dashboard, default_id)
    return None
