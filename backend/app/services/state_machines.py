"""Business state machines aligned with dashboards/app/js/app.js."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _now_reject_at() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")


def _find_hitl(dashboard: dict[str, Any], hitl_id: str) -> dict[str, Any] | None:
    for item in dashboard.get("hitlQueue", []):
        if item.get("id") == hitl_id:
            return item
    return None


def _find_project(dashboard: dict[str, Any], project_id: str) -> dict[str, Any] | None:
    for project in dashboard.get("projects", []):
        if project.get("id") == project_id:
            return project
    return None


def _get_closure(dashboard: dict[str, Any], project_id: str) -> dict[str, Any] | None:
    return dashboard.get("closure", {}).get(project_id)


def approve_hitl(dashboard: dict[str, Any], hitl_id: str) -> dict[str, Any]:
    item = _find_hitl(dashboard, hitl_id)
    if item is None:
        raise ValueError("HITL_NOT_FOUND")
    if item.get("approved"):
        raise ValueError("HITL_ALREADY_APPROVED")

    item["approved"] = True
    project_id = item.get("projectId")
    hitl_type = item.get("type", "")

    if hitl_type == "HITL-Artifact":
        from app.services.artifact_workflow import approve_artifact

        artifact_id = item.get("artifactId")
        if artifact_id:
            approve_artifact(dashboard, artifact_id, hitl_id=hitl_id)
        return {
            "nextAction": "open_workroom",
            "projectId": project_id,
            "artifactId": artifact_id,
            "hitlType": hitl_type,
        }

    for inbox_item in dashboard.get("inbox", []):
        if inbox_item.get("hitlId") == hitl_id:
            inbox_item["read"] = True
            inbox_item["status"] = "done"
            inbox_item["resolution"] = "approved"
            inbox_item["resolvedAt"] = _now_iso()

    project = _find_project(dashboard, project_id) if project_id else None
    if project:
        project["hitlPending"] = None
        project["progress"] = 92
        project["stage"] = "阶段5 · 结项交付"
        project["closureStatus"] = "in_closure"

    closure = _get_closure(dashboard, project_id) if project_id else None
    if closure:
        closure["status"] = "in_closure"
        hitl_type = item.get("type", "")
        for checklist_item in closure.get("checklist", []):
            label = checklist_item.get("label", "")
            if hitl_type and hitl_type in label:
                checklist_item["done"] = True
            if "HITL-3" in label or hitl_type in label:
                checklist_item["done"] = True
            if "验收" in label:
                checklist_item["done"] = True

    return {
        "patch": {
            "pulse": {
                "hitlPending": sum(
                    1 for p in dashboard.get("projects", []) if p.get("hitlPending")
                )
            },
            "projects": [project] if project else [],
            "closure": {project_id: closure} if project_id and closure else {},
        },
        "nextAction": "open_workroom",
        "projectId": project_id,
    }


def reject_hitl(
    dashboard: dict[str, Any], hitl_id: str, note: str | None = None
) -> dict[str, Any]:
    item = _find_hitl(dashboard, hitl_id)
    if item is None:
        raise ValueError("HITL_NOT_FOUND")
    if item.get("approved"):
        raise ValueError("HITL_ALREADY_APPROVED")

    reject_note = (note or "").strip() or "需修改后重新提交"

    if item.get("type") == "HITL-Artifact":
        from app.services.artifact_workflow import reject_artifact

        artifact_id = item.get("artifactId")
        if artifact_id:
            reject_artifact(dashboard, artifact_id, reject_note, hitl_id=hitl_id)
        item["approved"] = False
        item["rejected"] = True
        return {"hitlId": hitl_id, "artifactId": artifact_id, "note": reject_note}

    dashboard.setdefault("rejectHistory", []).insert(
        0,
        {
            "id": f"rej-{uuid4().hex[:8]}",
            "hitlId": hitl_id,
            "projectId": item.get("projectId"),
            "type": item.get("type"),
            "note": reject_note,
            "at": _now_reject_at(),
        },
    )

    for inbox_item in dashboard.get("inbox", []):
        if inbox_item.get("hitlId") == hitl_id:
            inbox_item["status"] = "done"
            inbox_item["resolution"] = "rejected"
            inbox_item["read"] = True

    return {"hitlId": hitl_id, "note": reject_note}


def patch_inbox(
    dashboard: dict[str, Any], inbox_id: str, patch: dict[str, Any]
) -> dict[str, Any]:
    for item in dashboard.get("inbox", []):
        if item.get("id") == inbox_id:
            item.update(patch)
            return item
    raise ValueError("INBOX_NOT_FOUND")


def resolve_inbox(
    dashboard: dict[str, Any], inbox_id: str, action: str
) -> dict[str, Any]:
    item = None
    for inbox_item in dashboard.get("inbox", []):
        if inbox_item.get("id") == inbox_id:
            item = inbox_item
            break
    if item is None:
        raise ValueError("INBOX_NOT_FOUND")

    item["status"] = "done"
    item["resolution"] = "approved" if action == "approve" else "discussed"
    item["resolvedAt"] = _now_iso()
    return item


def sanitize_ceo_thread(dashboard: dict[str, Any]) -> bool:
    """Remove orphan ack placeholders and empty CEO bubbles."""
    thread = dashboard.get("ceoThread", [])
    cleaned = [
        m
        for m in thread
        if not (
            m.get("direction") == "ceo_to_founder"
            and (
                m.get("type") == "ack"
                or not (m.get("text") or "").strip()
            )
        )
    ]
    if len(cleaned) != len(thread):
        dashboard["ceoThread"] = cleaned
        return True
    return False


def submit_ceo_brief(dashboard: dict[str, Any], text: str) -> dict[str, Any]:
    sanitize_ceo_thread(dashboard)
    thread = dashboard.setdefault("ceoThread", [])
    thread.append(
        {
            "id": f"thread-{uuid4().hex[:8]}",
            "direction": "founder_to_ceo",
            "channel": "web",
            "text": text,
            "at": _now_iso(),
        }
    )
    reply = {
        "id": f"thread-{uuid4().hex[:8]}",
        "direction": "ceo_to_founder",
        "channel": "web",
        "type": "ack",
        "text": "…",
        "at": _now_iso(),
    }
    thread.append(reply)
    return {"messages": [thread[-2], reply]}


def send_weekly(dashboard: dict[str, Any]) -> dict[str, Any]:
    weekly = dashboard.get("weeklyReport")
    if weekly is None:
        raise ValueError("WEEKLY_NOT_FOUND")
    if weekly.get("status") == "sent":
        raise ValueError("WEEKLY_ALREADY_SENT")

    weekly["status"] = "sent"
    for item in dashboard.get("inbox", []):
        if item.get("weeklyReportId"):
            item["read"] = True
            item["status"] = "done"

    for role in dashboard.get("roles", []):
        if role.get("id") == "ceo":
            extras = role.setdefault("extras", {})
            extras["reportStatus"] = "本周周报已发送"
            break

    return {"weeklyReport": weekly}


def patch_closure_checklist(
    dashboard: dict[str, Any],
    project_id: str,
    item_id: str,
    *,
    done: bool = True,
) -> dict[str, Any]:
    closure = dashboard.get("closure", {}).get(project_id)
    if not closure:
        raise ValueError("CLOSURE_NOT_FOUND")
    item = next(
        (x for x in closure.get("checklist", []) if x.get("id") == item_id), None
    )
    if item is None:
        raise ValueError("CLOSURE_ITEM_NOT_FOUND")
    item["done"] = done
    return {"projectId": project_id, "itemId": item_id, "done": done}
