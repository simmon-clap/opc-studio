"""Finance summary endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.api.deps import fail, ok, run_mutation
from app.db import get_session
from app.presentation.finance import (
    build_finance_xlsx,
    finance_list_item,
    finance_summary_payload,
    get_finance_project,
    sync_finance,
)
from app.services.dashboard_store import get_dashboard

router = APIRouter(tags=["finance"])


class FinancePeriodPatch(BaseModel):
    periodType: str = Field(..., pattern="^(month|quarter)$")
    period: str = Field(..., min_length=4, max_length=10)


class CostBreakdownPatch(BaseModel):
    token: float | None = None
    external: float | None = None
    tax: float | None = None
    other: float | None = None


class FinanceProjectPatch(BaseModel):
    costBreakdown: CostBreakdownPatch | None = None
    advisory: str | None = None
    advisorySource: str | None = None
    taxRatePct: float | None = None


@router.get("/finance/summary")
def finance_summary(session: Session = Depends(get_session)):
    dashboard = get_dashboard(session)
    sync_finance(dashboard)
    return ok(finance_summary_payload(dashboard))


@router.get("/finance/projects")
def finance_projects(session: Session = Depends(get_session)):
    dashboard = get_dashboard(session)
    sync_finance(dashboard)
    items = [
        finance_list_item(r)
        for r in dashboard.get("costs", {}).get("byProject") or []
        if r.get("projectId") != "_internal"
    ]
    return ok({"items": items})


@router.get("/finance/projects/{project_id}")
def finance_project_detail(project_id: str, session: Session = Depends(get_session)):
    dashboard = get_dashboard(session)
    row = get_finance_project(dashboard, project_id)
    if row is None:
        raise fail("FINANCE_PROJECT_NOT_FOUND", "项目财务数据不存在", status=404)
    return ok(row)


@router.patch("/finance/period")
def patch_finance_period(body: FinancePeriodPatch, session: Session = Depends(get_session)):
    def _apply(dashboard: dict[str, Any]) -> dict[str, Any]:
        costs = dashboard.setdefault("costs", {})
        costs["periodType"] = body.periodType
        costs["period"] = body.period
        sync_finance(dashboard)
        return {"finance": finance_summary_payload(dashboard)}

    result = run_mutation(session, _apply)
    return ok(result)


@router.patch("/finance/projects/{project_id}")
def patch_finance_project(
    project_id: str,
    body: FinanceProjectPatch,
    session: Session = Depends(get_session),
):
    def _apply(dashboard: dict[str, Any]) -> dict[str, Any]:
        costs = dashboard.setdefault("costs", {})
        row = next(
            (r for r in costs.get("byProject") or [] if r.get("projectId") == project_id),
            None,
        )
        if row is None:
            raise ValueError("FINANCE_PROJECT_NOT_FOUND")
        if body.costBreakdown:
            bd = row.setdefault("costBreakdown", {})
            for key, val in body.costBreakdown.model_dump(exclude_none=True).items():
                bd[key] = val
        if body.advisory is not None:
            row["advisory"] = body.advisory[:120]
            row["advisorySource"] = body.advisorySource or "ops"
        if body.taxRatePct is not None:
            stmt = costs.setdefault("statement", {})
            stmt["taxRatePct"] = body.taxRatePct
        sync_finance(dashboard)
        return {"project": get_finance_project(dashboard, project_id)}

    try:
        result = run_mutation(session, _apply)
    except ValueError as exc:
        if str(exc) == "FINANCE_PROJECT_NOT_FOUND":
            raise fail("FINANCE_PROJECT_NOT_FOUND", "项目财务数据不存在", status=404) from exc
        raise
    return ok(result)


@router.get("/finance/export")
def export_finance(
    format: str = "xlsx",
    scope: str = "full",
    session: Session = Depends(get_session),
):
    if format != "xlsx":
        raise fail("UNSUPPORTED_FORMAT", "仅支持 format=xlsx", status=400)
    if scope not in ("full", "statement", "projects"):
        raise fail("UNSUPPORTED_SCOPE", "scope 须为 full|statement|projects", status=400)

    dashboard = get_dashboard(session)
    content = build_finance_xlsx(dashboard)
    period = dashboard.get("costs", {}).get("period") or "report"
    filename = f"opc-finance-{period}.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
