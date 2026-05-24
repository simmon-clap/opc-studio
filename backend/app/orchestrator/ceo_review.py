"""CEO internal artifact review — revision loop before Founder HITL."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session

from app.deliverables.validator import validate_content
from app.orchestrator.directives import RoleDirective

MAX_REVISION_ROUNDS = 2
MIN_PASS_SCORE = 72
BULLET_DRAFT_MAX_LINES = 8


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


@dataclass
class CeoReviewResult:
    action: str  # pass | revision | escalate
    note: str = ""
    directive: RoleDirective | None = None
    score: int = 0


def _append_review_note(artifact: dict[str, Any], note: str, *, passed: bool) -> None:
    artifact.setdefault("reviewNotes", []).insert(
        0,
        {
            "by": "ceo",
            "at": _now_iso(),
            "note": note,
            "passed": passed,
            "round": len(artifact.get("reviewNotes") or []) + 1,
        },
    )


def review_artifact(
    session: Session | None,
    dashboard: dict[str, Any],
    artifact: dict[str, Any],
    *,
    project_id: str,
) -> CeoReviewResult:
    kind = artifact.get("kind") or artifact.get("type") or ""
    template_id = artifact.get("templateId") or ""
    content = artifact.get("content") or ""
    quality = artifact.get("quality") or validate_content(kind, template_id, content)
    score = int(quality.get("score") or 0)

    revision_round = len(artifact.get("reviewNotes") or [])
    if revision_round >= MAX_REVISION_ROUNDS:
        return CeoReviewResult(
            action="escalate",
            note=f"已修订 {MAX_REVISION_ROUNDS} 轮仍未达标，请你介入。",
            score=score,
        )

    issues: list[str] = list(quality.get("issues") or [])
    profile = dashboard.get("founderProfile") or {}
    legal_prefs = (profile.get("deliverables") or {}).get("legal") or {}

    if kind == "nda" and legal_prefs.get("rejectBulletDraft"):
        lines = [ln for ln in content.splitlines() if ln.strip().startswith(("##", "-", "*", "1."))]
        if len(lines) <= BULLET_DRAFT_MAX_LINES and "双向" not in content:
            issues.append("NDA 过于简略，需使用双向专业模板")

    if score < MIN_PASS_SCORE or issues:
        note = "；".join(issues) if issues else f"质量分 {score}/100 未达标"
        role_id = artifact.get("roleId") or "legal"
        directive = RoleDirective(
            role_id=role_id,
            title=f"修订 · {artifact.get('title', kind)}",
            kind=kind or role_id,
        )
        _append_review_note(artifact, note, passed=False)
        artifact["status"] = "revision"
        artifact["ceoReviewScore"] = score
        return CeoReviewResult(
            action="revision",
            note=note,
            directive=directive,
            score=score,
        )

    artifact["status"] = "draft"
    artifact["ceoReviewScore"] = score
    _append_review_note(artifact, "CEO 内审通过", passed=True)
    return CeoReviewResult(action="pass", score=score)


async def review_artifact_async(
    session: Session | None,
    dashboard: dict[str, Any],
    artifact: dict[str, Any],
    *,
    project_id: str,
) -> CeoReviewResult:
    """Rules first; optional LLM overlay when CEO role has Key."""
    base = review_artifact(session, dashboard, artifact, project_id=project_id)
    if not session or base.action != "pass":
        return base
    try:
        from app.services.llm_client import LlmError, chat_completion
        from app.services.role_config_service import get_role_runtime_config

        cfg = get_role_runtime_config(session, dashboard, "ceo")
        if not cfg.is_configured:
            return base
        kind = artifact.get("kind") or artifact.get("type") or ""
        content = (artifact.get("content") or "")[:6000]
        prompt = (
            "你是 CEO 内审。仅输出 JSON："
            '{"action":"pass|revision","score":0-100,"note":"简短中文"}'
            f"\n\n产出类型：{kind}\n\n{content}"
        )
        resp = await chat_completion(
            cfg,
            [
                {"role": "system", "content": "CEO artifact reviewer"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=512,
        )
        raw = resp.content.strip()
        if raw.startswith("```"):
            parts = raw.split("```", 2)
            raw = parts[1] if len(parts) > 1 else raw
            if raw.lstrip().startswith("json"):
                raw = raw.lstrip()[4:]
        data = json.loads(raw.strip())
        score = int(data.get("score") or base.score)
        artifact["ceoReviewScore"] = score
        if data.get("action") == "revision" or score < MIN_PASS_SCORE:
            note = data.get("note") or f"LLM 评审 {score} 分"
            role_id = artifact.get("roleId") or "legal"
            _append_review_note(artifact, note, passed=False)
            artifact["status"] = "revision"
            return CeoReviewResult(
                action="revision",
                note=note,
                directive=RoleDirective(
                    role_id=role_id,
                    title=f"修订 · {artifact.get('title', kind)}",
                    kind=kind or role_id,
                ),
                score=score,
            )
        _append_review_note(artifact, data.get("note") or "LLM 内审通过", passed=True)
    except (LlmError, json.JSONDecodeError, KeyError, ValueError, TypeError):
        return base
    return base
