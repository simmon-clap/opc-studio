"""Inbox deduplication — collapse noisy duplicate active items."""

from __future__ import annotations

from typing import Any


def inbox_dedup_key(item: dict[str, Any]) -> str | None:
    """Stable key for items that should appear at most once while active."""
    if item.get("status") != "active":
        return None

    proposal = item.get("proposal") or {}
    if fp := proposal.get("fingerprint"):
        return f"proposal:{fp}"

    if commitment_id := item.get("commitmentId"):
        return f"commitment:{commitment_id}"

    if artifact_id := item.get("artifactId"):
        category = item.get("category") or ""
        if category in {"approval", "reminder"}:
            return f"artifact:{artifact_id}:{category}"

    project_id = item.get("projectId")
    category = item.get("category") or ""
    title = item.get("title") or ""

    if project_id and category == "reminder" and "HITL" in title:
        return f"hitl-reminder:{project_id}"

    if project_id and category == "approval" and item.get("hitlId"):
        return f"hitl-approval:{item['hitlId']}"

    if project_id and category == "approval" and "待批" in title:
        return f"project-approval:{project_id}:{title[:48]}"

    return None


def dedupe_active_inbox(dashboard: dict[str, Any]) -> int:
    """Archive duplicate active inbox rows; keep newest (first in list). Returns archived count."""
    seen: set[str] = set()
    archived = 0
    for item in dashboard.get("inbox", []):
        key = inbox_dedup_key(item)
        if not key:
            continue
        if key in seen:
            item["status"] = "archived"
            archived += 1
        else:
            seen.add(key)
    return archived
