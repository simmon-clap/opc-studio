"""Weekly report endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlmodel import Session

from app.api.deps import fail, ok, run_mutation
from app.db import get_session
from app.services import orchestrator_hooks
from app.services.dashboard_store import get_dashboard
from app.services.state_machines import send_weekly

router = APIRouter(tags=["weekly"])


@router.get("/weekly/current")
def get_current_weekly(session: Session = Depends(get_session)):
    dashboard = get_dashboard(session)
    weekly = dashboard.get("weeklyReport")
    if weekly is None:
        raise fail("WEEKLY_NOT_FOUND", "周报不存在", status=404)
    return ok(weekly)


@router.post("/weekly/current/send")
async def send_current_weekly(session: Session = Depends(get_session)):
    def _apply(dashboard):
        return send_weekly(dashboard)

    try:
        result = run_mutation(session, _apply)
    except ValueError as exc:
        code = str(exc)
        if code == "WEEKLY_NOT_FOUND":
            raise fail("WEEKLY_NOT_FOUND", "周报不存在", status=404) from exc
        if code == "WEEKLY_ALREADY_SENT":
            raise fail("WEEKLY_ALREADY_SENT", "周报已发送", status=409) from exc
        raise

    week = result.get("weeklyReport", {}).get("week")
    await orchestrator_hooks.on_weekly_sent(week)
    return ok(result)


@router.get("/weekly/current/export")
def export_weekly(
    format: str = Query("md", alias="format"),
    session: Session = Depends(get_session),
):
    dashboard = get_dashboard(session)
    wr = dashboard.get("weeklyReport")
    if wr is None:
        raise fail("WEEKLY_NOT_FOUND", "周报不存在", status=404)

    if format == "md":
        lines = [
            f"# OPC Studio CEO 周报 {wr.get('week', '')}",
            "",
            f"周期: {wr.get('period', '')}",
            "",
            "## Executive Summary",
            wr.get("summary", ""),
            "",
        ]
        for section in wr.get("sections", []):
            lines.append(f"## {section.get('title', '')}")
            lines.append(section.get("content", ""))
            lines.append("")
        return PlainTextResponse("\n".join(lines), media_type="text/markdown")

    raise fail("UNSUPPORTED_FORMAT", "仅支持 format=md", status=400)
