"""CEO deliberate — merge proposals (rules first, optional LLM)."""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlmodel import Session

from app.services.llm_client import LlmError, chat_completion
from app.services.runtime_settings import get_runtime_settings
from app.services.role_config_service import get_role_runtime_config

logger = logging.getLogger(__name__)

_PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


def _pick_primary(items: list[dict[str, Any]]) -> dict[str, Any]:
    return sorted(
        items,
        key=lambda i: (
            _PRIORITY_RANK.get((i.get("proposal") or {}).get("priority") or "medium", 1),
            i.get("at") or "",
        ),
    )[0]


def deliberate_merge_proposals(dashboard: dict[str, Any]) -> dict[str, Any]:
    """Collapse duplicate project proposals into one CEO-facing digest entry."""
    active = [
        i
        for i in dashboard.get("inbox") or []
        if i.get("category") == "proposal" and i.get("status") == "active"
    ]
    by_project: dict[str, list[dict[str, Any]]] = {}
    for item in active:
        pid = item.get("projectId") or "_global"
        by_project.setdefault(pid, []).append(item)

    merged = 0
    archived = 0
    for pid, items in by_project.items():
        if len(items) < 2:
            continue
        primary = _pick_primary(items)
        extras = [i for i in items if i["id"] != primary["id"]]
        bullets = [primary.get("preview") or primary.get("title") or ""]
        for extra in extras[:4]:
            bullets.append(extra.get("preview") or extra.get("title") or "")
        primary["title"] = f"CEO 合并建议 · {len(items)} 项"
        primary["preview"] = " · ".join(b for b in bullets if b)[:200]
        prop = primary.setdefault("proposal", {})
        prop["deliberated"] = True
        prop["mergedCount"] = len(items)
        for extra in extras:
            extra["status"] = "archived"
            extra["resolution"] = "merged"
            extra["mergedInto"] = primary["id"]
            archived += 1
        merged += 1

    return {"mergedGroups": merged, "archived": archived}


async def deliberate_ceo_llm(
    session: Session, dashboard: dict[str, Any]
) -> dict[str, Any]:
    """Optional LLM pass — annotate top proposals with CEO note (no auto act)."""
    settings = get_runtime_settings(dashboard)
    if not settings.get("agency", {}).get("ceoDeliberateUseLlm"):
        return {"usedLlm": False}

    cfg = get_role_runtime_config(session, dashboard, "ceo")
    if not cfg.is_configured:
        return {"usedLlm": False, "reason": "ceo_not_configured"}

    proposals = [
        i
        for i in dashboard.get("inbox") or []
        if i.get("category") == "proposal"
        and i.get("status") == "active"
        and not (i.get("proposal") or {}).get("ceoNote")
    ][:5]
    if not proposals:
        return {"usedLlm": False, "annotated": 0}

    brief_lines = []
    for item in proposals:
        prop = item.get("proposal") or {}
        brief_lines.append(
            f"- [{prop.get('priority')}] {item.get('title')} | action={prop.get('suggestedAction')} role={prop.get('suggestedRole')}"
        )

    prompt = (
        "你是 CEO。以下为系统观察产生的待办建议，请用 JSON 数组回复，每项含 inboxId 与 note（一句中文决策建议）。\n"
        + "\n".join(f"{p.get('id')}: {line}" for p, line in zip(proposals, brief_lines))
    )

    try:
        resp = await chat_completion(
            cfg,
            messages=[
                {"role": "system", "content": "只输出 JSON 数组，如 [{\"inboxId\":\"...\",\"note\":\"...\"}]"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        raw = (resp.content or "").strip()
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.startswith("json"):
                raw = raw[4:]
        notes = json.loads(raw)
        if not isinstance(notes, list):
            return {"usedLlm": False, "reason": "bad_json"}
        annotated = 0
        for entry in notes:
            if not isinstance(entry, dict):
                continue
            iid = entry.get("inboxId")
            note = entry.get("note")
            if not iid or not note:
                continue
            for item in proposals:
                if item.get("id") == iid:
                    item.setdefault("proposal", {})["ceoNote"] = str(note)[:200]
                    annotated += 1
                    break
        return {"usedLlm": True, "annotated": annotated}
    except (LlmError, json.JSONDecodeError) as exc:
        logger.warning("CEO deliberate LLM skipped: %s", exc)
        return {"usedLlm": False, "reason": str(exc)}


async def run_ceo_deliberate(session: Session, dashboard: dict[str, Any]) -> dict[str, Any]:
    merge_result = deliberate_merge_proposals(dashboard)
    llm_result = await deliberate_ceo_llm(session, dashboard)
    return {**merge_result, **llm_result}
