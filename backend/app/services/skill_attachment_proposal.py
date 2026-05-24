"""Detect SKILL.md attachments and create skill_proposal inbox items."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.presentation.skills import parse_skill_markdown


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def maybe_propose_skill_from_attachment(
    dashboard: dict[str, Any], attachment: dict[str, Any]
) -> dict[str, Any] | None:
    filename = (attachment.get("filename") or "").lower()
    text = attachment.get("extractedText") or ""
    if not text.strip():
        return None
    looks_like_skill = (
        filename.endswith("skill.md")
        or "id:" in text[:800]
        and ("tools:" in text[:1200] or "requiredCapabilities:" in text[:1200])
    )
    if not looks_like_skill:
        return None
    try:
        skill = parse_skill_markdown(text)
    except ValueError:
        return None
    item_id = f"inbox-skill-{uuid4().hex[:8]}"
    item = {
        "id": item_id,
        "category": "skill_proposal",
        "channel": "web",
        "title": f"安装 Skill：{skill.get('name') or skill.get('id')}",
        "preview": (skill.get("description") or text[:200]).strip(),
        "proposedSkill": {"rawMarkdown": text, **skill},
        "attachmentIds": [attachment.get("id")],
        "at": _now_iso(),
        "read": False,
        "status": "active",
    }
    dashboard.setdefault("inbox", []).insert(0, item)
    return item
