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
    summary["totalTokens"] = int(summary.get("totalTokens") or 0) + input_tokens + output_tokens
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
    role_row["tokens"] = int(role_row.get("tokens") or 0) + input_tokens + output_tokens
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
            }
            by_project.append(proj_row)
        proj_row["tokens"] = int(proj_row.get("tokens") or 0) + input_tokens + output_tokens
        proj_row["cost"] = float(proj_row.get("cost") or 0) + cost_cny
        if proj_row.get("revenue"):
            proj_row["margin"] = float(proj_row.get("revenue") or 0) - float(
                proj_row.get("cost") or 0
            )

    total = float(summary.get("totalCost") or 1)
    for row in by_role:
        row["sharePct"] = round(float(row.get("cost") or 0) / total * 100, 1) if total else 0
