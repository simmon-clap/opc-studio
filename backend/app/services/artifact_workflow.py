"""Artifact review workflow — HITL binding and approval."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

REVIEW_KINDS = frozenset({"nda", "contract", "sow", "prd", "acceptance"})
AUTO_HITL_MIN_SCORE = 40


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _find_artifact(dashboard: dict[str, Any], artifact_id: str) -> dict[str, Any] | None:
    return next((a for a in dashboard.get("artifacts", []) if a.get("id") == artifact_id), None)


def maybe_submit_artifact_review(
    dashboard: dict[str, Any],
    artifact: dict[str, Any],
    project_id: str,
) -> dict[str, Any] | None:
    """Create HITL-Artifact + inbox when deliverable needs Founder sign-off."""
    kind = artifact.get("kind") or artifact.get("type") or ""
    if kind not in REVIEW_KINDS:
        return None
    if artifact.get("hitlId") or artifact.get("status") == "approved":
        return None

    score = (artifact.get("quality") or {}).get("score", 0)
    if score < AUTO_HITL_MIN_SCORE:
        artifact["status"] = "draft"
        return None

    project = next((p for p in dashboard.get("projects", []) if p.get("id") == project_id), {})
    client = (project.get("clientName") or project_id).replace("（线索）", "")
    hitl_id = f"hitl-art-{uuid4().hex[:6]}"
    kind_label = {
        "nda": "NDA",
        "contract": "合同",
        "sow": "SOW",
        "prd": "PRD",
        "acceptance": "验收报告",
    }.get(kind, artifact.get("title", "产出物"))

    dashboard.setdefault("hitlQueue", []).insert(
        0,
        {
            "id": hitl_id,
            "type": "HITL-Artifact",
            "projectId": project_id,
            "artifactId": artifact.get("id"),
            "artifactKind": kind,
            "title": f"审 {client} · {kind_label}",
            "summary": f"{artifact.get('title')} v{artifact.get('version', '0.1')} · 质量 {(artifact.get('quality') or {}).get('score', '—')}/100",
            "submittedBy": artifact.get("roleId") or "ceo",
            "submittedAt": _now_iso(),
            "artifacts": [artifact.get("id")],
        },
    )

    dashboard.setdefault("inbox", []).insert(
        0,
        {
            "id": f"inbox-{uuid4().hex[:8]}",
            "category": "approval",
            "from": artifact.get("roleId") or "ceo",
            "channel": "web",
            "title": f"待批 · {client} {kind_label}",
            "preview": (artifact.get("content") or "")[:80],
            "projectId": project_id,
            "artifactId": artifact.get("id"),
            "hitlId": hitl_id,
            "at": _now_iso(),
            "read": False,
            "status": "active",
        },
    )

    artifact["status"] = "review"
    artifact["hitlId"] = hitl_id
    return {"hitlId": hitl_id, "artifactId": artifact.get("id")}


def approve_artifact(
    dashboard: dict[str, Any],
    artifact_id: str,
    *,
    hitl_id: str | None = None,
) -> dict[str, Any]:
    art = _find_artifact(dashboard, artifact_id)
    if art is None:
        raise ValueError("ARTIFACT_NOT_FOUND")

    art["status"] = "approved"
    art["approvedAt"] = _now_iso()
    if hitl_id:
        for item in dashboard.get("hitlQueue", []):
            if item.get("id") == hitl_id:
                item["approved"] = True
        for inbox_item in dashboard.get("inbox", []):
            if inbox_item.get("hitlId") == hitl_id or inbox_item.get("artifactId") == artifact_id:
                inbox_item["read"] = True
                inbox_item["status"] = "done"
                inbox_item["resolution"] = "approved"
                inbox_item["resolvedAt"] = _now_iso()

    return {"artifactId": artifact_id, "status": "approved", "hitlId": hitl_id}


def reject_artifact(
    dashboard: dict[str, Any],
    artifact_id: str,
    note: str,
    *,
    hitl_id: str | None = None,
) -> dict[str, Any]:
    art = _find_artifact(dashboard, artifact_id)
    if art is None:
        raise ValueError("ARTIFACT_NOT_FOUND")

    art["status"] = "draft"
    art.pop("hitlId", None)
    art.setdefault("rejectNotes", []).insert(
        0, {"note": note, "at": _now_iso(), "hitlId": hitl_id}
    )

    if hitl_id:
        for inbox_item in dashboard.get("inbox", []):
            if inbox_item.get("hitlId") == hitl_id:
                inbox_item["status"] = "done"
                inbox_item["resolution"] = "rejected"
                inbox_item["read"] = True

    return {"artifactId": artifact_id, "status": "draft", "note": note}
