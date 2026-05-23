"""Delivery / HITL rule scan — inbox cues without LLM."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlmodel import Session

from app.services.dashboard_store import mutate
from app.services.inbox_dedup import dedupe_active_inbox, inbox_dedup_key


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _has_active_inbox_key(dashboard: dict[str, Any], key: str) -> bool:
    for item in dashboard.get("inbox", []):
        if item.get("status") != "active":
            continue
        if inbox_dedup_key(item) == key:
            return True
    return False


def tick_delivery(session: Session) -> dict[str, Any]:
    created = 0
    archived = 0
    with mutate(session) as dashboard:
        archived = dedupe_active_inbox(dashboard)

        for project in dashboard.get("projects", []):
            project_id = project.get("id")
            if not project_id or not project.get("hitlPending"):
                continue
            client = (project.get("clientName") or project_id).replace("（线索）", "")
            dedup_key = f"hitl-reminder:{project_id}"
            if _has_active_inbox_key(dashboard, dedup_key):
                continue
            dashboard.setdefault("inbox", []).insert(
                0,
                {
                    "id": f"inbox-{uuid4().hex[:8]}",
                    "category": "reminder",
                    "from": "ceo",
                    "channel": "web",
                    "title": f"交付提醒 · {client} HITL 待批",
                    "preview": f"项目 {project.get('hitlPending')} 等待 Founder 审批",
                    "projectId": project_id,
                    "at": _now_iso(),
                    "read": False,
                    "status": "active",
                },
            )
            created += 1

        for art in dashboard.get("artifacts", []):
            if art.get("status") != "review" or art.get("hitlId"):
                continue
            project_id = art.get("projectId")
            artifact_id = art.get("id")
            if not project_id or not artifact_id:
                continue
            dedup_key = f"artifact:{artifact_id}:approval"
            if _has_active_inbox_key(dashboard, dedup_key):
                continue
            dashboard.setdefault("inbox", []).insert(
                0,
                {
                    "id": f"inbox-{uuid4().hex[:8]}",
                    "category": "approval",
                    "from": art.get("roleId") or "ceo",
                    "channel": "web",
                    "title": f"内审待批 · {art.get('title', '产出物')}",
                    "preview": (art.get("content") or "")[:80],
                    "projectId": project_id,
                    "artifactId": artifact_id,
                    "at": _now_iso(),
                    "read": False,
                    "status": "active",
                },
            )
            created += 1

    return {"remindersCreated": created, "archivedDuplicates": archived}
