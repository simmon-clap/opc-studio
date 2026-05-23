"""Scheduler ticks — overdue reminders and daily digest cues."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.commitments import list_commitments, overdue_commitments


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _today_key() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")


def run_scheduler_tick(dashboard: dict[str, Any]) -> dict[str, Any]:
    """Scan commitments and open questions; write inbox reminders. Idempotent per day."""
    meta = dashboard.setdefault("meta", {})
    scheduler_meta = meta.setdefault("scheduler", {})
    today = _today_key()
    created = 0

    for item in overdue_commitments(dashboard):
        marker = f"overdue:{item['id']}"
        if marker in scheduler_meta.get("sent", []):
            continue
        _insert_reminder(
            dashboard,
            title=f"逾期 · {item.get('what', '承诺事项')}",
            preview=f"项目 {item.get('projectId')} · 负责人 {item.get('ownerRole')}",
            project_id=item.get("projectId"),
            commitment_id=item.get("id"),
            category="reminder",
        )
        scheduler_meta.setdefault("sent", []).append(marker)
        created += 1

    if scheduler_meta.get("dailyDigestDate") != today:
        open_items = list_commitments(dashboard, status="open")
        if open_items:
            summary = f"今日待跟进 {len(open_items)} 项"
            preview = "；".join(i.get("what", "")[:30] for i in open_items[:3])
            _insert_reminder(
                dashboard,
                title=f"CEO 每日摘要 · {summary}",
                preview=preview,
                project_id=None,
                commitment_id=None,
                category="digest",
            )
        scheduler_meta["dailyDigestDate"] = today
        created += 1

    meta["scheduler"] = scheduler_meta
    return {"remindersCreated": created, "date": today}


from uuid import uuid4


def _insert_reminder(
    dashboard: dict[str, Any],
    *,
    title: str,
    preview: str,
    project_id: str | None,
    commitment_id: str | None,
    category: str,
) -> None:
    for item in dashboard.get("inbox", []):
        if item.get("title") == title and item.get("status") == "active":
            return
    entry = {
        "id": f"inbox-{uuid4().hex[:8]}",
        "category": category,
        "from": "ceo",
        "channel": "web",
        "title": title,
        "preview": preview[:120],
        "at": _now_iso(),
        "read": False,
        "status": "active",
    }
    if project_id:
        entry["projectId"] = project_id
    if commitment_id:
        entry["commitmentId"] = commitment_id
    dashboard.setdefault("inbox", []).insert(0, entry)
