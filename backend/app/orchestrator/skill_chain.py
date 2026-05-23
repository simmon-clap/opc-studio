"""Skill chain executor — Epic 5."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from sqlmodel import Session

from app.presentation.skills import get_skill, sync_skill_catalog
from app.runners.base import RunContext, RunResult
from app.runners.registry import run_role


@dataclass
class ChainStepResult:
    step_index: int
    skill_id: str
    run_result: RunResult
    artifact_id: str | None = None


@dataclass
class ChainExecutionResult:
    chain_id: str
    steps: list[ChainStepResult] = field(default_factory=list)
    status: str = "completed"
    error: str | None = None


def get_chain(dashboard: dict[str, Any], chain_id: str) -> dict[str, Any] | None:
    sync_skill_catalog(dashboard)
    return next(
        (c for c in dashboard.get("skillChains", []) if c.get("id") == chain_id),
        None,
    )


async def execute_skill_chain(
    session: Session,
    dashboard: dict[str, Any],
    *,
    chain_id: str,
    role_id: str,
    project_id: str,
    base_task: dict[str, Any],
) -> ChainExecutionResult:
    chain = get_chain(dashboard, chain_id)
    if chain is None:
        return ChainExecutionResult(chain_id=chain_id, status="failed", error="CHAIN_NOT_FOUND")

    steps = chain.get("steps") or []
    results: list[ChainStepResult] = []
    previous_artifact_id: str | None = None

    for idx, step in enumerate(steps):
        skill_id = step.get("skillId")
        if not skill_id:
            continue
        skill = get_skill(dashboard, skill_id)
        if skill is None:
            on_fail = step.get("onFail") or "halt"
            if on_fail == "halt":
                return ChainExecutionResult(
                    chain_id=chain_id,
                    steps=results,
                    status="failed",
                    error=f"SKILL_NOT_FOUND:{skill_id}",
                )
            continue

        task = dict(base_task)
        task["id"] = task.get("id") or f"chain-{uuid4().hex[:8]}"
        task["roleId"] = role_id
        task["skillId"] = skill_id
        task["skillChainId"] = chain_id
        task["skillChainStep"] = idx
        if previous_artifact_id:
            task["previousArtifactId"] = previous_artifact_id

        ctx = RunContext(dashboard, project_id, task)
        run_result = await run_role(session, ctx)
        step_result = ChainStepResult(
            step_index=idx,
            skill_id=skill_id,
            run_result=run_result,
            artifact_id=run_result.artifact_id,
        )
        results.append(step_result)
        previous_artifact_id = run_result.artifact_id

        if run_result.artifact_id is None and step.get("onFail") == "halt":
            return ChainExecutionResult(
                chain_id=chain_id,
                steps=results,
                status="failed",
                error=f"STEP_FAILED:{skill_id}",
            )

    return ChainExecutionResult(chain_id=chain_id, steps=results, status="completed")
