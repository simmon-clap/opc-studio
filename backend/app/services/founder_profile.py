"""Founder preferences — explicit + confirmed suggestions only."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def get_profile(dashboard: dict[str, Any]) -> dict[str, Any]:
    from app.services.dashboard_normalize import _default_founder_profile

    profile = dashboard.get("founderProfile")
    if not profile:
        profile = _default_founder_profile()
    else:
        profile = dict(profile)
    if not (profile.get("document") or "").strip():
        profile["document"] = compose_profile_document(profile)
    return profile


def compose_profile_document(profile: dict[str, Any]) -> str:
    """Render structured profile + learned notes as an editable Markdown document."""
    comm = profile.get("communication") or {}
    legal = (profile.get("deliverables") or {}).get("legal") or {}
    esc = profile.get("escalation") or {}
    hitl = esc.get("alwaysHitlFor") or []
    lines = [
        "# Founder Profile",
        "",
        "CEO 与你的协作约定。用 Markdown 自由书写，保存后各轮 CEO 决策会读取本文档。",
        "",
        "## 沟通",
    ]
    if comm.get("preferConcise"):
        lines.append("- 回复简洁，先结论")
    max_sent = comm.get("maxReplySentences")
    if max_sent:
        lines.append(f"- CEO 单条回复不超过 {max_sent} 句")
    if len(lines) == 4:
        lines.append("- （在此补充沟通偏好）")

    lines.extend(["", "## 交付物偏好"])
    if legal.get("preferMutualNdaTemplate"):
        lines.append("- 法务 NDA 默认用双向专业模板")
    if legal.get("rejectBulletDraft"):
        lines.append("- 不要 bullet 草稿式法务文档")
    if lines[-1] == "## 交付物偏好":
        lines.append("- （在此补充交付标准）")

    lines.extend(["", "## 升级与审批"])
    if hitl:
        lines.append(f"- 以下类型必须经你 HITL 批准：{', '.join(hitl)}")
    else:
        lines.append("- （在此补充必须上报的事项）")

    lines.extend(["", "## 已确认偏好"])
    notes = profile.get("learnedNotes") or []
    if notes:
        for note in notes:
            text = (note.get("note") or "").strip()
            if text:
                lines.append(f"- {text}")
    else:
        lines.append("- （CEO 从对话中建议、经你采纳的内容会追加在此）")

    return "\n".join(lines)


def append_profile_document_line(profile: dict[str, Any], line: str) -> None:
    text = (line or "").strip()
    if not text:
        return
    doc = (profile.get("document") or compose_profile_document(profile)).rstrip()
    marker = "## 已确认偏好"
    placeholder = "- （CEO 从对话中建议、经你采纳的内容会追加在此）"
    if marker in doc:
        head, tail = doc.split(marker, 1)
        tail = tail.replace(placeholder, "").strip()
        tail_lines = [ln for ln in tail.splitlines() if ln.strip()]
        tail_lines.append(f"- {text}")
        profile["document"] = f"{head.rstrip()}\n\n{marker}\n" + "\n".join(tail_lines) + "\n"
    else:
        profile["document"] = f"{doc}\n\n{marker}\n- {text}\n"


def update_profile(dashboard: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    profile = dict(get_profile(dashboard))
    for key, value in patch.items():
        if key == "document":
            profile["document"] = str(value or "")
            continue
        if isinstance(value, dict) and isinstance(profile.get(key), dict):
            profile[key] = {**profile[key], **value}
        else:
            profile[key] = value
    if "document" not in patch and not (profile.get("document") or "").strip():
        profile["document"] = compose_profile_document(profile)
    dashboard["founderProfile"] = profile
    return profile


def profile_summary_for_prompt(dashboard: dict[str, Any]) -> str:
    profile = get_profile(dashboard)
    doc = (profile.get("document") or "").strip()
    if doc:
        return doc
    lines = ["Founder 偏好："]
    comm = profile.get("communication") or {}
    if comm.get("preferConcise"):
        lines.append("- 回复简洁，先结论")
    legal = (profile.get("deliverables") or {}).get("legal") or {}
    if legal.get("preferMutualNdaTemplate"):
        lines.append("- 法务 NDA 用双向专业模板")
    if legal.get("rejectBulletDraft"):
        lines.append("- 拒绝 bullet 草稿式法务文档")
    notes = profile.get("learnedNotes") or []
    for note in notes[-5:]:
        if note.get("note"):
            lines.append(f"- {note['note']}")
    return "\n".join(lines) if len(lines) > 1 else "（默认偏好）"


def suggest_profile_delta(
    dashboard: dict[str, Any],
    *,
    note: str,
    source: str,
    delta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    suggestion = {
        "id": f"psug-{uuid4().hex[:8]}",
        "note": note,
        "source": source,
        "delta": delta or {},
        "status": "pending",
        "createdAt": _now_iso(),
    }
    dashboard.setdefault("profileSuggestions", []).insert(0, suggestion)
    dashboard.setdefault("inbox", []).insert(
        0,
        {
            "id": f"inbox-{uuid4().hex[:8]}",
            "category": "profile_suggestion",
            "from": "ceo",
            "channel": "web",
            "title": "CEO 建议记住你的偏好",
            "preview": note[:80],
            "profileSuggestionId": suggestion["id"],
            "at": _now_iso(),
            "read": False,
            "status": "active",
        },
    )
    return suggestion


def adopt_suggestion(dashboard: dict[str, Any], suggestion_id: str) -> dict[str, Any] | None:
    suggestion = _find_suggestion(dashboard, suggestion_id)
    if not suggestion or suggestion.get("status") != "pending":
        return None
    profile = dict(get_profile(dashboard))
    delta = suggestion.get("delta") or {}
    note = suggestion.get("note")
    if note:
        profile.setdefault("learnedNotes", []).insert(
            0,
            {"at": _now_iso(), "note": note, "source": suggestion.get("source")},
        )
        append_profile_document_line(profile, note)
    for key, value in delta.items():
        if isinstance(value, dict) and isinstance(profile.get(key), dict):
            profile[key] = {**profile[key], **value}
        else:
            profile[key] = value
    dashboard["founderProfile"] = profile
    suggestion["status"] = "adopted"
    suggestion["resolvedAt"] = _now_iso()
    _resolve_inbox(dashboard, suggestion_id, "adopted")
    return suggestion


def dismiss_suggestion(dashboard: dict[str, Any], suggestion_id: str) -> dict[str, Any] | None:
    suggestion = _find_suggestion(dashboard, suggestion_id)
    if not suggestion:
        return None
    suggestion["status"] = "dismissed"
    suggestion["resolvedAt"] = _now_iso()
    _resolve_inbox(dashboard, suggestion_id, "dismissed")
    return suggestion


def _find_suggestion(dashboard: dict[str, Any], suggestion_id: str) -> dict[str, Any] | None:
    return next(
        (s for s in dashboard.get("profileSuggestions", []) if s.get("id") == suggestion_id),
        None,
    )


def _resolve_inbox(dashboard: dict[str, Any], suggestion_id: str, resolution: str) -> None:
    for item in dashboard.get("inbox", []):
        if item.get("profileSuggestionId") == suggestion_id:
            item["status"] = "done"
            item["read"] = True
            item["resolution"] = resolution
            item["resolvedAt"] = _now_iso()
