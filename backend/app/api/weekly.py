"""Weekly report endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlmodel import Session

from app.api.deps import fail, ok, run_mutation
from app.db import get_session
from app.presentation.weekly import (
    get_current_weekly_report,
    get_weekly_report,
    sync_weekly_reports,
    weekly_list_item,
)
from app.services import orchestrator_hooks
from app.services.dashboard_store import get_dashboard
from app.services.state_machines import send_weekly

router = APIRouter(tags=["weekly"])


@router.get("/weekly")
def list_weekly(session: Session = Depends(get_session)):
    dashboard = get_dashboard(session)
    sync_weekly_reports(dashboard)
    items = [weekly_list_item(r) for r in dashboard.get("weeklyReports") or []]
    return ok({"items": items})


@router.get("/weekly/current")
def get_current_weekly(session: Session = Depends(get_session)):
    dashboard = get_dashboard(session)
    weekly = get_current_weekly_report(dashboard)
    if weekly is None:
        raise fail("WEEKLY_NOT_FOUND", "周报不存在", status=404)
    return ok(weekly)


@router.post("/weekly/current/send")
async def send_current_weekly(session: Session = Depends(get_session)):
    def _apply(dashboard):
        return send_weekly(dashboard)

    try:
        result, patch = run_mutation(session, _apply, patch_domains=["inbox", "pulse", "ceo"])
    except ValueError as exc:
        code = str(exc)
        if code == "WEEKLY_NOT_FOUND":
            raise fail("WEEKLY_NOT_FOUND", "周报不存在", status=404) from exc
        if code == "WEEKLY_ALREADY_SENT":
            raise fail("WEEKLY_ALREADY_SENT", "周报已发送", status=409) from exc
        raise

    week = result.get("weeklyReport", {}).get("week")
    await orchestrator_hooks.on_weekly_sent(week)
    return ok(result, patch=patch)


@router.get("/weekly/current/export")
def export_weekly(
    format: str = Query("md", alias="format"),
    session: Session = Depends(get_session),
):
    dashboard = get_dashboard(session)
    wr = get_current_weekly_report(dashboard)
    if wr is None:
        raise fail("WEEKLY_NOT_FOUND", "周报不存在", status=404)

    if format == "md":
        lines = _weekly_to_md_lines(wr)
        return PlainTextResponse("\n".join(lines), media_type="text/markdown")

    raise fail("UNSUPPORTED_FORMAT", "仅支持 format=md", status=400)


@router.get("/weekly/{report_id}")
def get_weekly(report_id: str, session: Session = Depends(get_session)):
    dashboard = get_dashboard(session)
    report = get_weekly_report(dashboard, report_id)
    if report is None:
        raise fail("WEEKLY_NOT_FOUND", "周报不存在", status=404)
    return ok(report)


def _weekly_to_md_lines(wr: dict) -> list[str]:
    lines = [
        f"# OPC Studio CEO 周报 {wr.get('week', '')}",
        "",
        f"周期: {wr.get('period', '')}",
        "",
        "## 总述",
        wr.get("summary", ""),
        "",
    ]
    for block in wr.get("blocks") or []:
        lines.append(f"## {block.get('title', '')}")
        kind = block.get("kind")
        if kind == "projects":
            for item in block.get("items") or []:
                lines.append(
                    f"- {item.get('label')} {item.get('progress', 0)}% — {item.get('text', '')}"
                )
        elif kind == "risks":
            for item in block.get("items") or []:
                lines.append(f"- [{item.get('level', 'medium')}] {item.get('text', '')}")
        elif kind == "finance":
            lines.append(block.get("text") or "")
            for m in block.get("metrics") or []:
                lines.append(f"- {m.get('label')}: {m.get('value')}")
        elif kind == "outlook":
            for i, item in enumerate(block.get("items") or [], 1):
                lines.append(f"{i}. {item}")
        elif kind == "highlights":
            for item in block.get("items") or []:
                lines.append(f"- {item.get('roleId')}: {item.get('text')}")
        lines.append("")
    for section in wr.get("sections") or []:
        lines.append(f"## {section.get('title', '')}")
        lines.append(section.get("content", ""))
        lines.append("")
    return lines
