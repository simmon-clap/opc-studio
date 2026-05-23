"""Execute proposal → dispatch_task."""

from __future__ import annotations

from typing import Any

from app.orchestrator import dispatcher

_KIND_BY_SIGNAL = {
    "artifact.missing": "prd",
    "nda.stale": "nda",
    "pipeline.process": "prd",
    "build.missing": "demo",
    "deploy.pending": "acceptance",
}


def execute_proposal_dispatch(
    dashboard: dict[str, Any], inbox_item: dict[str, Any]
) -> dict[str, Any] | None:
    proposal = inbox_item.get("proposal") or {}
    action = proposal.get("suggestedAction") or "review"
    if action != "dispatch":
        return None

    role_id = proposal.get("suggestedRole") or inbox_item.get("from") or "ceo"
    if role_id == "ceo" and proposal.get("suggestedRole"):
        role_id = proposal["suggestedRole"]

    project_id = inbox_item.get("projectId")
    if not project_id:
        projects = dashboard.get("projects") or []
        project_id = projects[0]["id"] if projects else "proj-beta"

    title = (proposal.get("suggestedTitle") or inbox_item.get("title") or "Agency 派活").strip()
    if title.startswith("建议："):
        title = title[3:].strip()
    if title.startswith("建议 CEO 关注："):
        title = title.replace("建议 CEO 关注：", "", 1).strip()

    signal_type = proposal.get("signalType") or ""
    deliverable_kind = _KIND_BY_SIGNAL.get(signal_type)
    if not deliverable_kind and "nda" in title.lower():
        deliverable_kind = "nda"
    if not deliverable_kind and "prd" in title.lower():
        deliverable_kind = "prd"

    task = dispatcher.dispatch_task(
        dashboard,
        role_id=role_id,
        project_id=project_id,
        title=title,
        deliverable_kind=deliverable_kind,
    )
    task["agencySource"] = {
        "inboxId": inbox_item.get("id"),
        "signalType": signal_type,
        "fingerprint": proposal.get("fingerprint"),
    }
    return task
