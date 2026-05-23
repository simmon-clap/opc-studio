"""Computed artifact actions and export formats for Workroom v2."""

from __future__ import annotations

from typing import Any

REVIEW_KINDS = frozenset({"nda", "contract", "sow", "prd", "acceptance"})


def artifact_status_dot(art: dict[str, Any]) -> str:
    status = art.get("status") or "draft"
    pending = int(art.get("pendingFields") or (art.get("quality") or {}).get("pendingFields") or 0)
    if status == "review" or (status == "draft" and pending > 0):
        return "waiting"
    if status == "approved":
        return "done"
    if status == "revision":
        return "revision"
    return "active"


def artifact_export_formats(art: dict[str, Any]) -> list[dict[str, str]]:
    formats: list[dict[str, str]] = [
        {"id": "md", "label": "Markdown"},
        {"id": "pdf", "label": "PDF"},
    ]
    if art.get("files"):
        formats.append({"id": "zip", "label": "文件包 ZIP"})
    if art.get("demoUrl") or (art.get("content") or "").find("http") >= 0:
        formats.append({"id": "link", "label": "复制 Demo 链接"})
    return formats


def artifact_actions(art: dict[str, Any]) -> list[dict[str, Any]]:
    status = art.get("status") or "draft"
    pending = int(art.get("pendingFields") or (art.get("quality") or {}).get("pendingFields") or 0)
    kind = art.get("kind") or art.get("type") or "doc"
    actions: list[dict[str, Any]] = []

    if status == "review" and art.get("hitlId"):
        actions.append(
            {"id": "approve", "label": "批准", "actor": "founder", "primary": True}
        )
        actions.append({"id": "reject", "label": "驳回", "actor": "founder"})
        return actions

    if status == "revision":
        return actions

    if status in {"draft", "approved"} or pending > 0:
        if status != "approved":
            label = "填写" if pending > 0 else "编辑"
            actions.append(
                {"id": "edit", "label": label, "actor": "founder", "primary": True}
            )
        if (
            status == "draft"
            and not art.get("hitlId")
            and kind in REVIEW_KINDS
        ):
            actions.append(
                {"id": "submit_review", "label": "提交评审", "actor": "founder"}
            )

    return actions
