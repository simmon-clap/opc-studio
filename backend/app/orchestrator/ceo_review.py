"""CEO internal artifact review — revision loop before Founder HITL."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

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
