"""Overview dispatch feed — conversational dialogue between roles."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

MAX_FEED = 40

ASSIGN_LINES = (
    "{target}，{client}这边请帮忙{task}，今天尽快出一版。",
    "{target}，{client} · {task}，麻烦接一下。",
    "@{target} {client}的项目：{task}，交给你了。",
)

REPLY_LINES = (
    "收到，{task}我这就开始。",
    "明白，{task}交给我。",
    "OK，我先看材料再动手。",
)

DELIVER_LINES = (
    "{task}初稿好了，请你过目。",
    "这边{task}搞定了，{note}",
    "交付一下：{task} — {note}",
)

FAIL_LINES = (
    "抱歉，{task}这边卡住了：{reason}",
    "{task}没跑通，{reason}",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _short_task(title: str) -> str:
    text = (title or "").strip()
    if " · " in text:
        return text.split(" · ", 1)[-1].strip()
    return text[:80] or "这项任务"


def _role_name(dashboard: dict[str, Any], role_id: str) -> str:
    role = next((r for r in dashboard.get("roles", []) if r.get("id") == role_id), {})
    return role.get("name") or role_id


def _client_name(dashboard: dict[str, Any], project_id: str) -> str:
    project = next(
        (p for p in dashboard.get("projects", []) if p.get("id") == project_id),
        {},
    )
    return (project.get("clientName") or project_id).replace("（线索）", "")


def _pick_variant(lines: tuple[str, ...], seed: str) -> str:
    if not lines:
        return ""
    idx = sum(ord(c) for c in seed) % len(lines)
    return lines[idx]


def compose_assign_dialogue(
    dashboard: dict[str, Any],
    *,
    from_role: str,
    to_role: str,
    title: str,
    project_id: str,
    task_id: str,
) -> str:
    template = _pick_variant(ASSIGN_LINES, task_id or title)
    return template.format(
        target=_role_name(dashboard, to_role),
        client=_client_name(dashboard, project_id),
        task=_short_task(title),
    )


def compose_reply_dialogue(
    dashboard: dict[str, Any],
    *,
    role_id: str,
    title: str,
    task_id: str,
) -> str:
    template = _pick_variant(REPLY_LINES, task_id or role_id)
    return template.format(task=_short_task(title))


def normalize_feed_item(item: dict[str, Any]) -> dict[str, Any]:
    """Migrate legacy feed rows to conversational shape."""
    tone_map = {"assign": "assign", "accept": "reply", "complete": "deliver", "fail": "fail"}
    tone = item.get("tone") or tone_map.get(item.get("kind") or "", "reply")
    speaker = item.get("speakerRole")
    if not speaker:
        speaker = item.get("fromRole") if tone == "assign" else item.get("toRole") or item.get("fromRole")
    peer = item.get("peerRole") or item.get("toRole") or item.get("fromRole") or speaker
    text = (item.get("text") or item.get("message") or "").strip()
    out = {**item, "tone": tone, "speakerRole": speaker, "peerRole": peer, "text": text}
    if tone == "assign":
        out["fromRole"] = speaker
        out["toRole"] = peer
    return out


def _task_by_id(dashboard: dict[str, Any], task_id: str | None) -> dict[str, Any] | None:
    if not task_id:
        return None
    return next((t for t in dashboard.get("tasks", []) if t.get("id") == task_id), None)


def _last_activity_message(task: dict[str, Any]) -> str:
    activities = task.get("activities") or []
    if not activities:
        return ""
    return str(activities[-1].get("message") or "")


def _task_outcome(task: dict[str, Any] | None) -> str:
    if not task:
        return "missing"
    status = task.get("status")
    if status in {"running", "pending", "blocked"}:
        return status
    if status != "done":
        return status or "missing"
    last_msg = _last_activity_message(task)
    if last_msg.startswith("失败："):
        return "failed"
    if "CEO 要求修订" in last_msg:
        return "superseded"
    return "done"


def is_dispatch_item_consistent(dashboard: dict[str, Any], item: dict[str, Any]) -> bool:
    """Whether a feed line should still show given live task / orchestration state."""
    normalized = normalize_feed_item(item)
    tone = normalized.get("tone")
    task = _task_by_id(dashboard, normalized.get("taskId"))
    if not task:
        return False
    outcome = _task_outcome(task)
    status = task.get("status")

    if tone == "assign":
        return status in {"running", "pending"}
    if tone == "reply":
        return status == "running"
    if tone == "deliver":
        return outcome == "done"
    if tone == "fail":
        return outcome == "failed"
    if outcome == "superseded":
        return False
    return False


def compose_fail_dialogue(
    dashboard: dict[str, Any],
    *,
    role_id: str,
    title: str,
    reason: str,
    task_id: str,
) -> str:
    task = _short_task(title)
    reason_text = (reason or "请稍后重试").strip().removeprefix("失败：")[:60]
    template = _pick_variant(FAIL_LINES, task_id or role_id)
    return template.format(task=task, reason=reason_text)


def compose_deliver_dialogue(
    dashboard: dict[str, Any],
    *,
    role_id: str,
    title: str,
    note: str,
    task_id: str,
) -> str:
    task = _short_task(title)
    note_text = (note or "请审阅").strip()
    if note_text in {"完成", "done"}:
        note_text = "请审阅"
    template = _pick_variant(DELIVER_LINES, task_id or note_text)
    return template.format(task=task, note=note_text)


def append_dispatch_feed(
    dashboard: dict[str, Any],
    *,
    speaker_role: str,
    text: str,
    project_id: str,
    tone: str,
    peer_role: str | None = None,
    task_id: str | None = None,
) -> dict[str, Any]:
    """Append a chat-style line. tone: assign | reply | deliver (styling only)."""
    legacy_kind = {"assign": "assign", "reply": "accept", "deliver": "complete"}.get(
        tone, tone
    )
    item = {
        "id": f"df-{uuid4().hex[:8]}",
        "speakerRole": speaker_role,
        "peerRole": peer_role or speaker_role,
        "text": text[:160],
        "tone": tone,
        "projectId": project_id,
        "taskId": task_id,
        "at": _now_iso(),
        # legacy fields for older frontends / migrations
        "kind": legacy_kind,
        "fromRole": speaker_role if tone == "assign" else speaker_role,
        "toRole": peer_role or speaker_role,
        "message": text[:160],
    }
    if tone == "assign":
        item["fromRole"] = speaker_role
        item["toRole"] = peer_role or speaker_role
    feed = dashboard.setdefault("dispatchFeed", [])
    feed.insert(0, item)
    del feed[MAX_FEED:]
    return item


def log_assign(
    dashboard: dict[str, Any],
    *,
    to_role: str,
    title: str,
    project_id: str,
    task_id: str,
    from_role: str = "ceo",
) -> dict[str, Any]:
    text = compose_assign_dialogue(
        dashboard,
        from_role=from_role,
        to_role=to_role,
        title=title,
        project_id=project_id,
        task_id=task_id,
    )
    return append_dispatch_feed(
        dashboard,
        speaker_role=from_role,
        peer_role=to_role,
        text=text,
        project_id=project_id,
        tone="assign",
        task_id=task_id,
    )


def log_accept(
    dashboard: dict[str, Any],
    *,
    role_id: str,
    task: dict[str, Any],
    project_id: str,
) -> dict[str, Any] | None:
    task_id = task.get("id")
    if not task_id:
        return None
    feed = dashboard.get("dispatchFeed") or []
    if any(
        item.get("taskId") == task_id
        and (item.get("tone") == "reply" or item.get("kind") == "accept")
        for item in feed
    ):
        return None
    text = compose_reply_dialogue(
        dashboard,
        role_id=role_id,
        title=task.get("title") or "",
        task_id=task_id,
    )
    return append_dispatch_feed(
        dashboard,
        speaker_role=role_id,
        peer_role="ceo",
        text=text,
        project_id=project_id,
        tone="reply",
        task_id=task_id,
    )


def _has_feed_tone(dashboard: dict[str, Any], task_id: str, tone: str) -> bool:
    legacy = {"reply": "accept", "deliver": "complete", "fail": "fail"}
    feed = dashboard.get("dispatchFeed") or []
    for item in feed:
        if item.get("taskId") != task_id:
            continue
        item_tone = item.get("tone") or legacy.get(item.get("kind") or "")
        if item_tone == tone or item.get("kind") == legacy.get(tone):
            return True
    return False


def log_complete(
    dashboard: dict[str, Any],
    *,
    role_id: str,
    task: dict[str, Any],
    project_id: str,
    note: str = "完成",
) -> dict[str, Any] | None:
    task_id = task.get("id")
    if not task_id:
        return None
    if _has_feed_tone(dashboard, task_id, "deliver"):
        return None
    if _task_outcome(task) in {"failed", "superseded"}:
        return None
    text = compose_deliver_dialogue(
        dashboard,
        role_id=role_id,
        title=task.get("title") or "",
        note=note,
        task_id=task_id,
    )
    return append_dispatch_feed(
        dashboard,
        speaker_role=role_id,
        peer_role="ceo",
        text=text,
        project_id=project_id,
        tone="deliver",
        task_id=task_id,
    )


def log_task_failed(
    dashboard: dict[str, Any],
    *,
    role_id: str,
    task: dict[str, Any],
    project_id: str,
    reason: str,
) -> dict[str, Any] | None:
    task_id = task.get("id")
    if not task_id:
        return None
    if _has_feed_tone(dashboard, task_id, "fail"):
        return None
    text = compose_fail_dialogue(
        dashboard,
        role_id=role_id,
        title=task.get("title") or "",
        reason=reason,
        task_id=task_id,
    )
    return append_dispatch_feed(
        dashboard,
        speaker_role=role_id,
        peer_role="ceo",
        text=text,
        project_id=project_id,
        tone="fail",
        task_id=task_id,
    )


def reconcile_dispatch_feed(dashboard: dict[str, Any]) -> None:
    """Backfill missing dialogue lines from current task state (idempotent)."""
    if not dashboard.get("roles"):
        dashboard.setdefault("roles", [])
    for task in dashboard.get("tasks", []):
        role_id = task.get("roleId")
        project_id = task.get("projectId")
        task_id = task.get("id")
        if not role_id or not project_id or not task_id or role_id == "ceo":
            continue
        status = task.get("status")
        title = task.get("title") or "任务"

        if status in {"running", "pending"}:
            if not _has_feed_tone(dashboard, task_id, "assign"):
                log_assign(
                    dashboard,
                    to_role=role_id,
                    title=title,
                    project_id=project_id,
                    task_id=task_id,
                )
            if status == "running" and not _has_feed_tone(dashboard, task_id, "reply"):
                log_accept(
                    dashboard,
                    role_id=role_id,
                    task=task,
                    project_id=project_id,
                )


def sync_dispatch_feed(dashboard: dict[str, Any]) -> None:
    """Normalize legacy rows and align feed with live tasks / orchestration."""
    feed = dashboard.setdefault("dispatchFeed", [])
    dashboard["dispatchFeed"] = [normalize_feed_item(item) for item in feed]
    reconcile_dispatch_feed(dashboard)


def bootstrap_dispatch_feed(dashboard: dict[str, Any]) -> None:
    """Legacy alias — always reconcile so feed matches tasks."""
    sync_dispatch_feed(dashboard)


def set_orchestration_active(dashboard: dict[str, Any], active: bool) -> None:
    meta = dashboard.setdefault("meta", {})
    meta["orchestrationActive"] = bool(active)
    if active:
        meta["orchestrationStartedAt"] = _now_iso()
    else:
        meta["orchestrationEndedAt"] = _now_iso()


def feed_signature(dashboard: dict[str, Any]) -> str:
    from app.services.overview_presenter import compute_overview_live

    feed = dashboard.get("dispatchFeed") or []
    meta = dashboard.get("meta") or {}
    tasks = dashboard.get("tasks") or []
    live = dashboard.get("presentation", {}).get("overview") or dashboard.get("overviewLive")
    if not live:
        from app.presentation.overview import compute_overview_live

        live = compute_overview_live(dashboard)
    running = sum(1 for t in tasks if t.get("status") == "running")
    pending = sum(1 for t in tasks if t.get("status") == "pending")
    live_ids = ",".join(d.get("id", "") for d in live.get("dialogues", [])[:8])
    edge_ids = ",".join(
        f"{e.get('fromRole')}->{e.get('toRole')}" for e in live.get("activeEdges", [])[:8]
    )
    return (
        f"{len(feed)}:{live_ids}:{edge_ids}:"
        f"{meta.get('orchestrationActive')}:{running}:{pending}"
    )
