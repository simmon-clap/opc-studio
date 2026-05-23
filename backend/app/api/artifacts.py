"""Artifact content endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session

from app.api.deps import fail, ok, run_mutation
from app.db import get_session
from app.deliverables.validator import validate_content
from app.services import orchestrator_hooks
from app.services.artifact_versions import (
    append_version,
    diff_versions,
    ensure_versions_meta,
)
from app.services.artifact_workflow import approve_artifact, maybe_submit_artifact_review
from app.services.dashboard_store import get_dashboard
from app.presentation.artifact_actions import artifact_actions, artifact_export_formats
from app.services.project_store import (
    get_artifact_meta,
    read_artifact_file,
    read_artifact_files,
    sync_artifact_to_dashboard,
    write_artifact_file,
)

router = APIRouter(tags=["artifacts"])


class ContentBody(BaseModel):
    content: str
    note: str | None = None


@router.get("/projects/{project_id}/artifacts/{artifact_id}")
def get_artifact_meta_route(
    project_id: str,
    artifact_id: str,
    session: Session = Depends(get_session),
):
    dashboard = get_dashboard(session)
    art = get_artifact_meta(dashboard, project_id, artifact_id)
    if art is None:
        raise fail("ARTIFACT_NOT_FOUND", "产出物不存在", status=404)
    ensure_versions_meta(art, project_id)
    row = {k: v for k, v in art.items() if k != "content"}
    row["actions"] = artifact_actions(art)
    row["exportFormats"] = artifact_export_formats(art)
    return ok(row)


@router.get("/projects/{project_id}/artifacts/{artifact_id}/content")
def get_artifact_content(
    project_id: str,
    artifact_id: str,
    version: str | None = Query(None),
    session: Session = Depends(get_session),
):
    dashboard = get_dashboard(session)
    art = get_artifact_meta(dashboard, project_id, artifact_id)
    if art is None:
        raise fail("ARTIFACT_NOT_FOUND", "产出物不存在", status=404)

    from app.services.artifact_versions import get_version_content

    if version:
        content = get_version_content(project_id, artifact_id, version)
    else:
        content = read_artifact_file(project_id, artifact_id)
    if content is None:
        content = art.get("content", "")

    files = art.get("files") or read_artifact_files(project_id, artifact_id)
    return ok(
        {
            "content": content,
            "artifactId": artifact_id,
            "projectId": project_id,
            "version": version or art.get("version"),
            "files": files,
            "images": art.get("images") or [],
        }
    )


@router.get("/projects/{project_id}/artifacts/{artifact_id}/versions")
def list_artifact_versions(
    project_id: str,
    artifact_id: str,
    session: Session = Depends(get_session),
):
    dashboard = get_dashboard(session)
    art = get_artifact_meta(dashboard, project_id, artifact_id)
    if art is None:
        raise fail("ARTIFACT_NOT_FOUND", "产出物不存在", status=404)
    ensure_versions_meta(art, project_id)
    return ok(
        {
            "current": art.get("version"),
            "versions": art.get("versions") or [],
        }
    )


@router.get("/projects/{project_id}/artifacts/{artifact_id}/diff")
def artifact_diff(
    project_id: str,
    artifact_id: str,
    from_version: str = Query(..., alias="from"),
    to_version: str = Query(..., alias="to"),
    session: Session = Depends(get_session),
):
    dashboard = get_dashboard(session)
    if get_artifact_meta(dashboard, project_id, artifact_id) is None:
        raise fail("ARTIFACT_NOT_FOUND", "产出物不存在", status=404)
    return ok(diff_versions(project_id, artifact_id, from_version, to_version))


@router.put("/projects/{project_id}/artifacts/{artifact_id}/content")
async def put_artifact_content(
    project_id: str,
    artifact_id: str,
    body: ContentBody,
    session: Session = Depends(get_session),
):
    dashboard = get_dashboard(session)
    art = get_artifact_meta(dashboard, project_id, artifact_id)
    if art is None:
        raise fail("ARTIFACT_NOT_FOUND", "产出物不存在", status=404)

    write_artifact_file(project_id, artifact_id, body.content)

    def _update(dashboard):
        row = sync_artifact_to_dashboard(dashboard, project_id, artifact_id, body.content)
        if row:
            ensure_versions_meta(row, project_id)
            append_version(
                row,
                body.content,
                author="founder",
                note=body.note or "Founder 编辑",
                project_id=project_id,
            )
            q = validate_content(
                row.get("kind", "doc"),
                row.get("templateId", "generic.markdown"),
                body.content,
            )
            row["quality"] = {
                "score": q["score"],
                "sectionsOk": q["sectionsOk"],
                "pendingFields": q["pendingFields"],
                "issues": q["issues"],
            }
            row["status"] = "draft" if row.get("status") == "approved" else q["status"]

    run_mutation(session, _update)
    await orchestrator_hooks.on_artifact_updated(project_id, artifact_id)
    return ok({"artifactId": artifact_id, "projectId": project_id})


@router.post("/projects/{project_id}/artifacts/{artifact_id}/submit-review")
def submit_artifact_review(
    project_id: str,
    artifact_id: str,
    session: Session = Depends(get_session),
):
    def _apply(dashboard):
        art = get_artifact_meta(dashboard, project_id, artifact_id)
        if art is None:
            raise ValueError("ARTIFACT_NOT_FOUND")
        result = maybe_submit_artifact_review(dashboard, art, project_id)
        return result or {"artifactId": artifact_id, "status": art.get("status")}

    try:
        result = run_mutation(session, _apply)
    except ValueError as exc:
        if str(exc) == "ARTIFACT_NOT_FOUND":
            raise fail("ARTIFACT_NOT_FOUND", "产出物不存在", status=404) from exc
        raise
    return ok(result)


@router.post("/projects/{project_id}/artifacts/{artifact_id}/approve")
def approve_artifact_route(
    project_id: str,
    artifact_id: str,
    session: Session = Depends(get_session),
):
    def _apply(dashboard):
        art = get_artifact_meta(dashboard, project_id, artifact_id)
        if art is None:
            raise ValueError("ARTIFACT_NOT_FOUND")
        return approve_artifact(
            dashboard, artifact_id, hitl_id=art.get("hitlId")
        )

    try:
        result = run_mutation(session, _apply)
    except ValueError as exc:
        if str(exc) == "ARTIFACT_NOT_FOUND":
            raise fail("ARTIFACT_NOT_FOUND", "产出物不存在", status=404) from exc
        raise
    return ok(result)
