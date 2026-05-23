"""Agent run trace API."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.deps import fail, ok
from app.db import get_session
from app.models.agent_runs import AgentRun

router = APIRouter(tags=["agent-runs"])


@router.get("/agent-runs/{run_id}/trace")
def get_agent_run_trace(run_id: str, session: Session = Depends(get_session)):
    row = session.get(AgentRun, run_id)
    if row is None:
        raise fail("RUN_NOT_FOUND", "运行记录不存在", status=404)
    tool_calls = []
    if row.tool_calls_json:
        try:
            tool_calls = json.loads(row.tool_calls_json)
        except json.JSONDecodeError:
            tool_calls = []
    return ok(
        {
            "runId": row.id,
            "roleId": row.role_id,
            "projectId": row.project_id,
            "taskId": row.task_id,
            "skillId": row.skill_id,
            "model": row.model,
            "status": row.status,
            "inputTokens": row.input_tokens,
            "outputTokens": row.output_tokens,
            "costCny": row.cost_cny,
            "toolCalls": tool_calls,
            "startedAt": row.started_at.isoformat() if row.started_at else None,
            "finishedAt": row.finished_at.isoformat() if row.finished_at else None,
        }
    )
