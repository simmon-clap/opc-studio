"""Weekly report v2 presentation and normalization."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from app.config import MOCK_DASHBOARD_PATH

_DEPRECATED_WEEKLY_KEYS = (
    "pipelineSnapshot",
    "pendingDecisions",
    "financeSnapshot",
    "sections",
    "roleHighlights",
    "rolePerformance",
)


def _is_legacy_weekly_shape(dashboard: dict[str, Any]) -> bool:
    legacy = dashboard.get("weeklyReport") or {}
    reports = dashboard.get("weeklyReports") or []

    for key in _DEPRECATED_WEEKLY_KEYS:
        if key in legacy:
            return True
    for report in reports:
        if any(key in report for key in _DEPRECATED_WEEKLY_KEYS):
            return True
        if not (report.get("blocks") or []):
            return True

    if not reports:
        return bool(legacy) and not legacy.get("blocks")

    # Valid v2 weeklyReports[] — do not replace because mock has more history rows.
    return False


def _bootstrap_weekly_v2_from_mock(dashboard: dict[str, Any]) -> None:
    """Replace v1 weekly domain with mock v2 weeklyReports when DB predates WEEKLY-V2."""
    if not _is_legacy_weekly_shape(dashboard):
        return
    try:
        mock = json.loads(MOCK_DASHBOARD_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    mock_reports = mock.get("weeklyReports")
    if not mock_reports:
        return
    dashboard["weeklyReports"] = deepcopy(mock_reports)
    dashboard.pop("weeklyReport", None)


def _strip_deprecated_weekly_fields(report: dict[str, Any]) -> None:
    for key in _DEPRECATED_WEEKLY_KEYS:
        report.pop(key, None)


def sync_weekly_reports(dashboard: dict[str, Any]) -> None:
    """Ensure weeklyReports[] exists and weeklyReport alias points at current draft."""
    _bootstrap_weekly_v2_from_mock(dashboard)
    reports = dashboard.get("weeklyReports")
    legacy = dashboard.get("weeklyReport")
    if not reports and legacy:
        dashboard["weeklyReports"] = [_migrate_legacy_report(legacy)]
        reports = dashboard["weeklyReports"]
    if not reports:
        dashboard.pop("weeklyReport", None)
        return
    for report in reports:
        _strip_deprecated_weekly_fields(report)
    reports.sort(key=lambda r: r.get("week") or r.get("id") or "", reverse=True)
    draft = next((r for r in reports if r.get("status") == "draft"), None)
    dashboard["weeklyReport"] = draft or reports[0]
    _strip_deprecated_weekly_fields(dashboard["weeklyReport"])


def get_current_weekly_report(dashboard: dict[str, Any]) -> dict[str, Any] | None:
    sync_weekly_reports(dashboard)
    return dashboard.get("weeklyReport")


def get_weekly_report(dashboard: dict[str, Any], report_id: str) -> dict[str, Any] | None:
    sync_weekly_reports(dashboard)
    for report in dashboard.get("weeklyReports") or []:
        if report.get("id") == report_id or report.get("week") == report_id:
            return report
    wr = dashboard.get("weeklyReport")
    if wr and (wr.get("id") == report_id or wr.get("week") == report_id):
        return wr
    return None


def weekly_list_item(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": report.get("id") or report.get("week"),
        "week": report.get("week"),
        "period": report.get("period"),
        "status": report.get("status"),
        "summary": (report.get("summary") or "")[:120],
        "generatedAt": report.get("generatedAt"),
    }


def _migrate_legacy_report(legacy: dict[str, Any]) -> dict[str, Any]:
    """Convert v1 weeklyReport shape to v2 blocks (best effort)."""
    if legacy.get("blocks"):
        return legacy
    blocks: list[dict[str, Any]] = []
    pipeline = legacy.get("pipelineSnapshot") or []
    if pipeline:
        blocks.append(
            {
                "kind": "projects",
                "title": "项目进展",
                "roleId": "ceo",
                "items": [
                    {
                        "projectId": row.get("projectId"),
                        "label": row.get("label"),
                        "progress": row.get("progress", 0),
                        "text": row.get("note") or row.get("stage") or "",
                    }
                    for row in pipeline[:5]
                ],
            }
        )
    fs = legacy.get("financeSnapshot")
    if fs:
        blocks.append(
            {
                "kind": "finance",
                "title": "本周经营",
                "roleId": "ops",
                "text": f"合同 {fs.get('revenue', 0)} · 毛利 {fs.get('marginPct', 0)}%",
                "metrics": [{"label": "毛利", "value": f"{fs.get('marginPct', 0)}%"}],
                "costsLink": True,
            }
        )
    for sec in legacy.get("sections") or []:
        title = (sec.get("title") or "").lower()
        content = sec.get("content") or ""
        if "风险" in title:
            blocks.append(
                {
                    "kind": "risks",
                    "title": "风险与关注",
                    "roleId": "ceo",
                    "items": [{"level": "medium", "text": line.strip("-* ")[:200]} for line in content.split("\n") if line.strip()][:3],
                }
            )
        elif "计划" in title or "下周" in title:
            blocks.append(
                {
                    "kind": "outlook",
                    "title": "下周重点",
                    "roleId": "ceo",
                    "items": [line.strip("0123456789. ") for line in content.split("\n") if line.strip()][:3],
                }
            )
    highlights = legacy.get("roleHighlights") or []
    if highlights:
        blocks.append(
            {
                "kind": "highlights",
                "title": "部门一句",
                "roleId": "ceo",
                "collapsed": True,
                "items": [{"roleId": h.get("roleId"), "text": h.get("text")} for h in highlights[:5]],
            }
        )
    return {**legacy, "blocks": blocks}
