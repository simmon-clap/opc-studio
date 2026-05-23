"""Build normalized artifact records for dashboard + file storage."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.deliverables.kinds import DeliverableSpec, migrate_legacy_artifact, spec_for_kind
from app.deliverables.validator import validate_content
from app.services.artifact_versions import ensure_versions_meta


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def build_artifact_record(
    *,
    artifact_id: str,
    spec: DeliverableSpec,
    content: str,
    role_id: str,
    project_id: str,
    task_id: str | None = None,
    demo_url: str | None = None,
    files: list[dict[str, Any]] | None = None,
    images: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    quality = validate_content(spec.kind, spec.template_id, content)
    record: dict[str, Any] = {
        "id": artifact_id,
        "projectId": project_id,
        "kind": spec.kind,
        "format": spec.format,
        "viewer": spec.viewer,
        "group": spec.group,
        "type": spec.kind,
        "icon": spec.icon,
        "title": spec.title,
        "version": "0.1",
        "roleId": role_id,
        "templateId": spec.template_id,
        "status": quality["status"],
        "updatedAt": _now_iso(),
        "content": content,
        "quality": {
            "score": quality["score"],
            "sectionsOk": quality["sectionsOk"],
            "pendingFields": quality["pendingFields"],
            "issues": quality["issues"],
        },
    }
    if task_id:
        record["taskId"] = task_id
    if demo_url:
        record["demoUrl"] = demo_url
    if files:
        record["files"] = files
    if images:
        record["images"] = images
    if quality["pendingFields"]:
        record["pendingFields"] = quality["pendingFields"]
    return record


def normalize_dashboard_artifacts(dashboard: dict[str, Any]) -> int:
    updated = 0
    artifacts = dashboard.get("artifacts", [])
    for i, art in enumerate(artifacts):
        before = art.get("kind")
        migrate_legacy_artifact(art)
        ensure_versions_meta(art, art.get("projectId", ""))
        if not art.get("quality") and art.get("content"):
            spec = spec_for_kind(art.get("kind", "doc"), task_title=art.get("title", ""))
            q = validate_content(spec.kind, art.get("templateId", spec.template_id), art["content"])
            art["quality"] = {
                "score": q["score"],
                "sectionsOk": q["sectionsOk"],
                "pendingFields": q["pendingFields"],
                "issues": q["issues"],
            }
            art.setdefault("status", q["status"])
        if art.get("kind") != before:
            updated += 1
    return updated
