"""Project endpoints."""

from __future__ import annotations

import io
import zipfile
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session

from app.api.deps import fail, ok, run_mutation
from app.db import get_session
from app.services.dashboard_store import get_dashboard
from app.services.state_machines import patch_closure_checklist
from app.services.project_store import (
    deliveries_dir,
    ensure_project_dirs,
    get_artifact_meta,
    read_artifact_file,
)

router = APIRouter(tags=["projects"])


class ClosureCheckBody(BaseModel):
    done: bool = True


@router.patch("/projects/{project_id}/closure/checklist/{item_id}")
def patch_closure_item(
    project_id: str,
    item_id: str,
    body: ClosureCheckBody,
    session: Session = Depends(get_session),
):
    def _apply(dashboard):
        return patch_closure_checklist(
            dashboard, project_id, item_id, done=body.done
        )

    try:
        result = run_mutation(session, _apply)
    except ValueError as exc:
        code = str(exc)
        if code == "CLOSURE_NOT_FOUND":
            raise fail("CLOSURE_NOT_FOUND", "结项清单不存在", status=404)
        raise fail("CLOSURE_ITEM_NOT_FOUND", "结项项不存在", status=404)
    return ok(result)


@router.get("/projects")
def list_projects(session: Session = Depends(get_session)):
    dashboard = get_dashboard(session)
    return ok(dashboard.get("projects", []))


@router.get("/projects/{project_id}")
def get_project(project_id: str, session: Session = Depends(get_session)):
    dashboard = get_dashboard(session)
    for project in dashboard.get("projects", []):
        if project.get("id") == project_id:
            closure = dashboard.get("closure", {}).get(project_id)
            return ok({**project, "closure": closure})
    raise fail("PROJECT_NOT_FOUND", "项目不存在", status=404)


@router.get("/projects/{project_id}/artifacts")
def list_artifacts(project_id: str, session: Session = Depends(get_session)):
    dashboard = get_dashboard(session)
    items = [
        {k: v for k, v in art.items() if k != "content"}
        for art in dashboard.get("artifacts", [])
        if art.get("projectId") == project_id
    ]
    return ok(items)


@router.get("/projects/{project_id}/export")
def export_project(
    project_id: str,
    type: str = Query("internal", alias="type"),
    session: Session = Depends(get_session),
):
    dashboard = get_dashboard(session)
    project = next(
        (p for p in dashboard.get("projects", []) if p.get("id") == project_id),
        None,
    )
    if project is None:
        raise fail("PROJECT_NOT_FOUND", "项目不存在", status=404)

    ensure_project_dirs(project_id)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for art in dashboard.get("artifacts", []):
            if art.get("projectId") != project_id:
                continue
            aid = art.get("id")
            content = read_artifact_file(project_id, aid)
            if content is None:
                content = art.get("content", "")
            filename = f"{aid}.md"
            if type == "client" and art.get("demoUrl"):
                content = f"{content}\n\nDemo URL: {art['demoUrl']}\n"
            zf.writestr(filename, content)

        meta = {
            "projectId": project_id,
            "clientName": project.get("clientName"),
            "exportedAt": datetime.now(timezone.utc).isoformat(),
            "type": type,
        }
        zf.writestr("manifest.json", str(meta))

    buf.seek(0)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"{project_id}_{type}_{stamp}.zip"
    deliveries = deliveries_dir(project_id)
    deliveries.mkdir(parents=True, exist_ok=True)
    (deliveries / filename).write_bytes(buf.getvalue())
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
