"""Consume pending SQL handoffs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlmodel import Session, select

from app.models.handoffs import Handoff
from app.services.dashboard_store import mutate


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def tick_handoff(session: Session) -> dict[str, Any]:
    pending = session.exec(select(Handoff).where(Handoff.status == "pending")).all()
    consumed = 0
    for row in pending:
        payload: dict[str, Any] = {}
        if row.payload_json:
            try:
                payload = json.loads(row.payload_json)
            except json.JSONDecodeError:
                payload = {}

        with mutate(session) as dashboard:
            title = f"Handoff · {row.from_role_id} → {row.to_role_id}"
            preview = (payload.get("note") or payload.get("artifactId") or "")[:80]
            exists = any(
                i.get("handoffId") == row.id
                for i in dashboard.get("inbox", [])
                if i.get("status") == "active"
            )
            if not exists:
                entry: dict[str, Any] = {
                    "id": f"inbox-{uuid4().hex[:8]}",
                    "category": "handoff",
                    "from": row.from_role_id,
                    "to": row.to_role_id,
                    "channel": "web",
                    "title": title,
                    "preview": preview or "角色交接",
                    "projectId": row.project_id,
                    "handoffId": row.id,
                    "taskId": row.task_id,
                    "at": _now_iso(),
                    "read": False,
                    "status": "active",
                }
                if payload.get("artifactId"):
                    entry["artifactId"] = payload["artifactId"]
                dashboard.setdefault("inbox", []).insert(0, entry)

        row.status = "consumed"
        session.add(row)
        session.commit()
        consumed += 1

    return {"consumed": consumed}
