"""CEO thread and brief endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, File, Request, UploadFile
from pydantic import BaseModel
from sqlmodel import Session

from app.api.deps import fail, ok, run_mutation
from app.db import get_session
from app.services import orchestrator_hooks
from app.services.dashboard_store import get_dashboard, mutate
from app.services.ingress_documents import ingest_bytes
from app.services.state_machines import sanitize_ceo_thread, submit_ceo_brief

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ceo"])


class BriefBody(BaseModel):
    text: str
    attachmentIds: list[str] | None = None
    skillChainId: str | None = None


async def _run_plan_and_workflow_background(
    text: str, project_id: str, attachment_ids: list[str] | None = None
) -> None:
    logger.info("CEO background workflow start project=%s text=%s", project_id, text[:80])
    try:
        await orchestrator_hooks.on_ceo_brief_plan_and_workflow(
            text, project_id, attachment_ids=attachment_ids
        )
        logger.info("CEO background workflow done project=%s", project_id)
    except Exception:
        logger.exception("CEO plan/workflow background task failed")


def _ingest_upload(dashboard, upload: UploadFile, raw: bytes) -> str:
    try:
        rec = ingest_bytes(
            dashboard,
            filename=upload.filename or "upload.md",
            content=raw,
            content_type=upload.content_type,
        )
        return rec["id"]
    except ValueError as exc:
        code = str(exc)
        if code == "FILE_TOO_LARGE":
            raise fail("FILE_TOO_LARGE", "文件过大（最大 10MB）", status=413) from exc
        raise fail("UNSUPPORTED_FORMAT", "仅支持 Markdown 与 PDF", status=400) from exc


async def _run_ceo_chat_background(
    text: str, attachment_ids: list[str] | None = None
) -> None:
    logger.info("CEO chat background start text=%s", text[:80])
    try:
        chat_meta = await orchestrator_hooks.on_ceo_brief_chat(
            text, attachment_ids=attachment_ids
        )
        if chat_meta.get("scheduleWorkflow") and chat_meta.get("projectId"):
            await orchestrator_hooks.on_ceo_brief_plan_and_workflow(
                text, chat_meta["projectId"], attachment_ids=attachment_ids
            )
        logger.info("CEO chat background done project=%s", chat_meta.get("projectId"))
    except Exception:
        logger.exception("CEO chat background failed")
        _fail_pending_ceo_ack(str(text)[:40])


def _fail_pending_ceo_ack(hint: str = "") -> None:
    from datetime import datetime, timezone

    from app.db import session_scope
    from app.services.dashboard_store import mutate

    with session_scope() as session:
        with mutate(session) as dashboard:
            thread = dashboard.get("ceoThread", [])
            for msg in reversed(thread):
                if msg.get("direction") == "ceo_to_founder" and msg.get("type") == "ack":
                    msg["type"] = "analysis"
                    msg["text"] = "⚠️ CEO 回复失败，请稍后重试或检查 API 配置。"
                    msg["at"] = datetime.now(timezone.utc).astimezone().isoformat(
                        timespec="seconds"
                    )
                    return


async def _process_brief(
    session: Session,
    background_tasks: BackgroundTasks,
    text: str,
    attachment_ids: list[str] | None = None,
    skill_chain_id: str | None = None,
):
    text = text.strip()
    if not text and not attachment_ids:
        raise fail("INVALID_BRIEF", "消息不能为空")

    def _apply(dashboard):
        result = submit_ceo_brief(dashboard, text or "（附件）")
        if skill_chain_id:
            dashboard.setdefault("meta", {})["preferredSkillChainId"] = skill_chain_id
        return result

    _, patch = run_mutation(session, _apply, patch_domains=["ceo", "pulse", "inbox", "projects"])

    background_tasks.add_task(
        _run_ceo_chat_background,
        text or "请阅读附件",
        attachment_ids,
    )

    dashboard = get_dashboard(session)
    thread = dashboard.get("ceoThread", [])
    plan = dashboard.get("meta", {}).get("lastCeoTurn") or {}
    return ok(
        {
            "messages": thread[-2:] if len(thread) >= 2 else thread,
            "thread": thread,
            "projectId": dashboard.get("meta", {}).get("activeProjectId"),
        },
        patch=patch,
        processing=True,
        workflowPending=True,
        dispatchSummary={
            "shouldDispatch": plan.get("shouldDispatch"),
            "projectId": plan.get("projectId"),
        },
    )


@router.get("/ceo/thread")
def get_ceo_thread(session: Session = Depends(get_session)):
    def _clean(dashboard):
        if sanitize_ceo_thread(dashboard):
            return {"cleaned": True}
        return {"cleaned": False}

    _, patch = run_mutation(session, _clean, patch_domains=["ceo", "pulse"])
    dashboard = get_dashboard(session)
    return ok(dashboard.get("ceoThread", []), patch=patch)


@router.post("/ceo/brief")
async def post_ceo_brief(
    request: Request,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        form = await request.form()
        text = str(form.get("text") or "")
        skill_chain_id = str(form.get("skillChainId") or "").strip() or None
        upload_files = [f for f in form.getlist("files") if isinstance(f, UploadFile)]
        attachment_ids: list[str] = []
        with mutate(session) as dashboard:
            for upload in upload_files:
                raw = await upload.read()
                attachment_ids.append(_ingest_upload(dashboard, upload, raw))
        return await _process_brief(
            session, background_tasks, text, attachment_ids, skill_chain_id
        )

    body = BriefBody(**await request.json())
    merged_ids = list(body.attachmentIds or [])
    return await _process_brief(
        session, background_tasks, body.text, merged_ids or None, body.skillChainId
    )


@router.post("/ingress/attachments")
async def upload_attachment(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    raw = await file.read()

    def _apply(dashboard):
        return ingest_bytes(
            dashboard,
            filename=file.filename or "upload.md",
            content=raw,
            content_type=file.content_type,
        )

    try:
        result, patch = run_mutation(session, _apply, patch_domains=["inbox", "skills", "pulse"])
        return ok(result, patch=patch)
    except ValueError as exc:
        code = str(exc)
        if code == "FILE_TOO_LARGE":
            raise fail("FILE_TOO_LARGE", "文件过大（最大 10MB）", status=413) from exc
        raise fail("UNSUPPORTED_FORMAT", "仅支持 Markdown 与 PDF", status=400) from exc
