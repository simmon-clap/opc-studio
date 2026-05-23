"""Per-project structured brief — execution context."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def get_brief(dashboard: dict[str, Any], project_id: str) -> dict[str, Any]:
    briefs = dashboard.setdefault("projectBriefs", {})
    return briefs.get(project_id) or {}


def merge_brief_delta(
    dashboard: dict[str, Any], project_id: str, delta: dict[str, Any] | None
) -> dict[str, Any]:
    if not delta:
        return get_brief(dashboard, project_id)
    briefs = dashboard.setdefault("projectBriefs", {})
    current = dict(briefs.get(project_id) or {})
    for key, value in delta.items():
        if value is None:
            continue
        if key == "confirmedFacts" and isinstance(value, list):
            existing = list(current.get("confirmedFacts") or [])
            for fact in value:
                if fact and fact not in existing:
                    existing.append(fact)
            current["confirmedFacts"] = existing
        elif key == "openQuestions" and isinstance(value, list):
            current["openQuestions"] = value
        else:
            current[key] = value
    current["updatedAt"] = _now_iso()
    briefs[project_id] = current
    return current


def brief_context_for_prompt(dashboard: dict[str, Any], project_id: str) -> str:
    brief = get_brief(dashboard, project_id)
    if not brief:
        return "（尚无项目 Brief）"
    lines = [f"项目 {project_id} Brief："]
    for key in ("clientName", "cooperationMode", "ndaType", "scope"):
        if brief.get(key):
            lines.append(f"- {key}: {brief[key]}")
    if brief.get("confirmedFacts"):
        lines.append(f"- 已确认: {', '.join(brief['confirmedFacts'])}")
    if brief.get("openQuestions"):
        lines.append(f"- 待答: {', '.join(brief['openQuestions'])}")
    return "\n".join(lines)
