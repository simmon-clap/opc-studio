"""Commitment tracking — open loops, reminders, supervision."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

MAX_CLOSED_KEEP = 50


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def list_commitments(
    dashboard: dict[str, Any],
    *,
    status: str | None = None,
    project_id: str | None = None,
) -> list[dict[str, Any]]:
    items = dashboard.get("commitments", [])
    out: list[dict[str, Any]] = []
    for item in items:
        if status and item.get("status") != status:
            continue
        if project_id and item.get("projectId") != project_id:
            continue
        out.append(item)
    return out


def open_commitment(
    dashboard: dict[str, Any],
    *,
    project_id: str,
    what: str,
    owner_role: str,
    kind: str = "deliverable",
    due_at: str | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    record = {
        "id": f"cmt-{uuid4().hex[:8]}",
        "projectId": project_id,
        "what": what,
        "ownerRole": owner_role,
        "kind": kind,
        "status": "open",
        "dueAt": due_at,
        "linkedTaskId": None,
        "linkedArtifactId": None,
        "source": source,
        "createdAt": _now_iso(),
        "closedAt": None,
    }
    dashboard.setdefault("commitments", []).insert(0, record)
    return record


def link_commitment_task(
    dashboard: dict[str, Any], commitment_id: str, task_id: str
) -> None:
    item = _find(dashboard, commitment_id)
    if item:
        item["linkedTaskId"] = task_id


def link_commitment_artifact(
    dashboard: dict[str, Any], commitment_id: str, artifact_id: str
) -> None:
    item = _find(dashboard, commitment_id)
    if item:
        item["linkedArtifactId"] = artifact_id


def close_commitment(
    dashboard: dict[str, Any], commitment_id: str, *, reason: str = "done"
) -> dict[str, Any] | None:
    item = _find(dashboard, commitment_id)
    if not item or item.get("status") != "open":
        return item
    item["status"] = "closed"
    item["closedAt"] = _now_iso()
    item["closeReason"] = reason
    _trim_closed(dashboard)
    return item


def close_commitments_for_task(dashboard: dict[str, Any], task_id: str) -> int:
    closed = 0
    for item in dashboard.get("commitments", []):
        if item.get("status") == "open" and item.get("linkedTaskId") == task_id:
            item["status"] = "closed"
            item["closedAt"] = _now_iso()
            item["closeReason"] = "task_done"
            closed += 1
    if closed:
        _trim_closed(dashboard)
    return closed


def patch_commitment(
    dashboard: dict[str, Any],
    commitment_id: str,
    *,
    due_at: str | None = None,
    status: str | None = None,
) -> dict[str, Any] | None:
    item = _find(dashboard, commitment_id)
    if not item:
        return None
    if due_at is not None:
        item["dueAt"] = due_at
    if status == "closed":
        item["status"] = "closed"
        item["closedAt"] = _now_iso()
        _trim_closed(dashboard)
    return item


def apply_commitment_actions(
    dashboard: dict[str, Any],
    actions: list[dict[str, Any]],
    *,
    project_id: str,
    source: str | None = None,
) -> list[dict[str, Any]]:
    created: list[dict[str, Any]] = []
    for action in actions:
        if not isinstance(action, dict):
            continue
        op = (action.get("action") or "open").lower()
        if op == "close" and action.get("id"):
            close_commitment(dashboard, action["id"])
            continue
        if op != "open":
            continue
        what = (action.get("what") or "").strip()
        if not what:
            continue
        owner = action.get("ownerRole") or action.get("owner_role") or "ceo"
        created.append(
            open_commitment(
                dashboard,
                project_id=action.get("projectId") or project_id,
                what=what,
                owner_role=owner,
                kind=action.get("kind") or "deliverable",
                due_at=action.get("dueAt") or action.get("due_at"),
                source=source,
            )
        )
    return created


def overdue_commitments(dashboard: dict[str, Any]) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc).astimezone()
    out: list[dict[str, Any]] = []
    for item in dashboard.get("commitments", []):
        if item.get("status") != "open":
            continue
        due = item.get("dueAt")
        if not due:
            continue
        try:
            due_dt = datetime.fromisoformat(due)
            if due_dt <= now:
                out.append(item)
        except ValueError:
            continue
    return out


def _find(dashboard: dict[str, Any], commitment_id: str) -> dict[str, Any] | None:
    return next(
        (c for c in dashboard.get("commitments", []) if c.get("id") == commitment_id),
        None,
    )


def _trim_closed(dashboard: dict[str, Any]) -> None:
    items = dashboard.get("commitments", [])
    open_items = [i for i in items if i.get("status") == "open"]
    closed = [i for i in items if i.get("status") == "closed"]
    closed.sort(key=lambda x: x.get("closedAt") or "", reverse=True)
    dashboard["commitments"] = open_items + closed[:MAX_CLOSED_KEEP]
