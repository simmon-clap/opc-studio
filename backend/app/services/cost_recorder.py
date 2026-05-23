"""Record LLM token costs into dashboard aggregates."""

from __future__ import annotations

from typing import Any


def record_agent_cost(
    dashboard: dict[str, Any],
    *,
    role_id: str,
    project_id: str | None,
    input_tokens: int,
    output_tokens: int,
    cost_cny: float,
    model: str,
) -> None:
    costs = dashboard.setdefault("costs", {})
    summary = costs.setdefault("summary", {})
    token_delta = input_tokens + output_tokens
    summary["totalTokens"] = int(summary.get("totalTokens") or 0) + token_delta
    summary["totalCost"] = float(summary.get("totalCost") or 0) + cost_cny

    by_role = costs.setdefault("byRole", [])
    role_row = next((r for r in by_role if r.get("roleId") == role_id), None)
    if role_row is None:
        role_row = {
            "roleId": role_id,
            "tokens": 0,
            "cost": 0,
            "runs": 0,
            "model": model,
            "sharePct": 0,
        }
        by_role.append(role_row)
    role_row["tokens"] = int(role_row.get("tokens") or 0) + token_delta
    role_row["cost"] = float(role_row.get("cost") or 0) + cost_cny
    role_row["runs"] = int(role_row.get("runs") or 0) + 1
    role_row["model"] = model

    if project_id:
        by_project = costs.setdefault("byProject", [])
        proj_row = next(
            (r for r in by_project if r.get("projectId") == project_id), None
        )
        if proj_row is None:
            proj_row = {
                "projectId": project_id,
                "tokens": 0,
                "cost": 0,
                "sharePct": 0,
                "revenue": 0,
                "received": 0,
                "margin": 0,
                "costBreakdown": {"token": 0, "external": 0, "tax": 0, "other": 0},
                "byRole": [],
            }
            by_project.append(proj_row)
        proj_row["tokens"] = int(proj_row.get("tokens") or 0) + token_delta
        breakdown = proj_row.setdefault("costBreakdown", {"token": 0, "external": 0, "tax": 0, "other": 0})
        breakdown["token"] = float(breakdown.get("token") or 0) + cost_cny
        proj_row["cost"] = float(proj_row.get("cost") or 0) + cost_cny

        role_in_proj = next(
            (r for r in proj_row.setdefault("byRole", []) if r.get("roleId") == role_id),
            None,
        )
        if role_in_proj is None:
            role_in_proj = {"roleId": role_id, "tokens": 0, "cost": 0, "runs": 0, "sharePct": 0}
            proj_row["byRole"].append(role_in_proj)
        role_in_proj["tokens"] = int(role_in_proj.get("tokens") or 0) + token_delta
        role_in_proj["cost"] = float(role_in_proj.get("cost") or 0) + cost_cny
        role_in_proj["runs"] = int(role_in_proj.get("runs") or 0) + 1

    from app.presentation.finance import sync_finance

    sync_finance(dashboard)
