"""Overview live dialogues — derived from tasks + dispatch event log."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.presentation.schema import PRESENTATION_VERSION
from app.services.dispatch_feed import (
    compose_assign_dialogue,
    compose_reply_dialogue,
    normalize_feed_item,
)

MAX_DIALOGUES = 5
DELIVER_VISIBLE_SEC = 10
FAIL_VISIBLE_SEC = 10

ROLE_SLOTS = {rid: 0 for rid in ("ceo", "product", "legal", "dev", "ops")}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_at(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _feed_index(dashboard: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for raw in dashboard.get("dispatchFeed") or []:
        item = normalize_feed_item(raw)
        tid = item.get("taskId")
        if tid:
            index.setdefault(tid, []).append(item)
    return index


def _latest_tone(feed_items: list[dict[str, Any]], tone: str) -> dict[str, Any] | None:
    for item in feed_items:
        if item.get("tone") == tone:
            return item
    return None


def _task_outcome(task: dict[str, Any]) -> str:
    status = task.get("status")
    if status in {"running", "pending", "blocked"}:
        return status
    if status != "done":
        return status or "missing"
    activities = task.get("activities") or []
    last = str(activities[-1].get("message") or "") if activities else ""
    if last.startswith("失败："):
        return "failed"
    if "CEO 要求修订" in last:
        return "superseded"
    return "done"


def _dialogue_text(
    dashboard: dict[str, Any],
    task: dict[str, Any],
    tone: str,
    feed_items: list[dict[str, Any]],
) -> str:
    cached = _latest_tone(feed_items, tone)
    if cached and cached.get("text"):
        return cached["text"]
    role_id = task.get("roleId") or "ceo"
    title = task.get("title") or "任务"
    project_id = task.get("projectId") or ""
    task_id = task.get("id") or ""
    if tone == "assign":
        return compose_assign_dialogue(
            dashboard,
            from_role="ceo",
            to_role=role_id,
            title=title,
            project_id=project_id,
            task_id=task_id,
        )
    if tone == "reply":
        return compose_reply_dialogue(
            dashboard,
            role_id=role_id,
            title=title,
            task_id=task_id,
        )
    if tone == "deliver":
        note = ""
        activities = task.get("activities") or []
        if activities:
            note = str(activities[-1].get("message") or "")
        from app.services.dispatch_feed import compose_deliver_dialogue

        return compose_deliver_dialogue(
            dashboard,
            role_id=role_id,
            title=title,
            note=note or "完成",
            task_id=task_id,
        )
    if tone == "fail":
        activities = task.get("activities") or []
        reason = ""
        if activities:
            reason = str(activities[-1].get("message") or "").removeprefix("失败：")
        from app.services.dispatch_feed import compose_fail_dialogue

        return compose_fail_dialogue(
            dashboard,
            role_id=role_id,
            title=title,
            reason=reason or "执行失败",
            task_id=task_id,
        )
    return title


def _edge_entry(from_role: str, to_role: str, project_id: str, tone: str) -> dict[str, Any]:
    return {
        "fromRole": from_role,
        "toRole": to_role,
        "projectId": project_id,
        "tone": tone,
    }


def _count_eligible_dialogues(dashboard: dict[str, Any]) -> int:
    """How many dialogues would show without the visible cap."""
    tasks = dashboard.get("tasks") or []
    used: set[str] = set()
    count = 0
    for task in tasks:
        if task.get("roleId") in {None, "ceo"}:
            continue
        st = task.get("status")
        if st == "running":
            rid = task.get("roleId") or ""
            if rid not in used:
                used.add(rid)
                count += 1
        elif st == "pending":
            rid = task.get("roleId") or ""
            if rid not in used:
                used.add(rid)
                count += 1
    return count


def compute_overview_live(dashboard: dict[str, Any]) -> dict[str, Any]:
    """Build versioned overview dialogue + edge model for the dashboard UI."""
    tasks = dashboard.get("tasks") or []
    feed = _feed_index(dashboard)
    now = _now()

    dialogues: list[dict[str, Any]] = []
    active_edges: list[dict[str, Any]] = []
    used_roles: set[str] = set()
    slot_counter = dict(ROLE_SLOTS)

    def add_dialogue(
        *,
        task: dict[str, Any],
        tone: str,
        anchor: str,
        speaker: str,
        peer: str,
        visible_sec: int | None = None,
    ) -> None:
        if len(dialogues) >= MAX_DIALOGUES:
            return
        role_id = task.get("roleId") or speaker
        if anchor == "role" and role_id in used_roles:
            return
        if anchor == "role":
            used_roles.add(role_id)

        feed_items = feed.get(task.get("id") or "", [])
        slot = slot_counter.get(speaker, 0)
        slot_counter[speaker] = slot + 1

        at = _parse_at((_latest_tone(feed_items, tone) or {}).get("at"))
        if not at:
            at = _parse_at(task.get("startedAt")) or now

        item = {
            "id": f"live-{task.get('id')}-{tone}",
            "taskId": task.get("id"),
            "projectId": task.get("projectId"),
            "speakerRole": speaker,
            "peerRole": peer,
            "tone": tone,
            "text": _dialogue_text(dashboard, task, tone, feed_items),
            "anchor": anchor,
            "edgeFrom": "ceo" if tone == "assign" else speaker,
            "edgeTo": role_id if tone == "assign" else "ceo",
            "slot": slot,
            "at": at.astimezone().isoformat(timespec="seconds"),
        }
        if visible_sec is not None:
            item["visibleUntil"] = (at + timedelta(seconds=visible_sec)).astimezone().isoformat(
                timespec="seconds"
            )
        dialogues.append(item)

        if tone in {"assign", "reply"} and role_id != "ceo":
            edge = _edge_entry("ceo", role_id, task.get("projectId") or "", tone)
            edge_key = (edge["fromRole"], edge["toRole"], edge["projectId"])
            if edge_key not in {(e["fromRole"], e["toRole"], e["projectId"]) for e in active_edges}:
                active_edges.append(edge)

    running = sorted(
        [
            t
            for t in tasks
            if t.get("status") == "running" and t.get("roleId") not in {None, "ceo"}
        ],
        key=lambda t: t.get("startedAt") or "",
        reverse=True,
    )
    pending = sorted(
        [
            t
            for t in tasks
            if t.get("status") == "pending" and t.get("roleId") not in {None, "ceo"}
        ],
        key=lambda t: t.get("startedAt") or "",
        reverse=True,
    )

    for task in running:
        role_id = task.get("roleId") or ""
        add_dialogue(
            task=task,
            tone="reply",
            anchor="role",
            speaker=role_id,
            peer="ceo",
            visible_sec=None,
        )

    for task in pending:
        role_id = task.get("roleId") or ""
        if role_id in used_roles:
            continue
        add_dialogue(
            task=task,
            tone="assign",
            anchor="edge",
            speaker="ceo",
            peer=role_id,
            visible_sec=None,
        )

    done_recent = sorted(
        [t for t in tasks if _task_outcome(t) in {"done", "failed"}],
        key=lambda t: t.get("completedAt") or t.get("startedAt") or "",
        reverse=True,
    )
    for task in done_recent:
        if len(dialogues) >= MAX_DIALOGUES:
            break
        outcome = _task_outcome(task)
        if outcome == "superseded":
            continue
        role_id = task.get("roleId") or ""
        if role_id in used_roles or role_id == "ceo":
            continue
        feed_items = feed.get(task.get("id") or "", [])
        tone = "fail" if outcome == "failed" else "deliver"
        cached = _latest_tone(feed_items, tone)
        at = _parse_at((cached or {}).get("at")) or _parse_at(task.get("completedAt"))
        if not at:
            continue
        ttl = FAIL_VISIBLE_SEC if tone == "fail" else DELIVER_VISIBLE_SEC
        if now - at.astimezone(timezone.utc) > timedelta(seconds=ttl + 2):
            continue
        add_dialogue(
            task=task,
            tone=tone,
            anchor="role",
            speaker=role_id,
            peer="ceo",
            visible_sec=ttl,
        )

    eligible = _count_eligible_dialogues(dashboard)
    return {
        "version": PRESENTATION_VERSION,
        "dialogues": dialogues[:MAX_DIALOGUES],
        "activeEdges": active_edges,
        "meta": {
            "visibleCap": MAX_DIALOGUES,
            "eligibleCount": eligible,
            "hiddenCount": max(0, eligible - len(dialogues)),
            "runningCount": len(running),
            "pendingCount": len(pending),
        },
    }
