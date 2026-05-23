"""Artifact / project gap agency rules."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

from app.agency.signals import Signal


def observe_artifact_gaps(
    dashboard: dict[str, Any], *, role_id: str
) -> list[Signal]:
    signals: list[Signal] = []
    now = datetime.now(timezone.utc)

    for project in dashboard.get("projects", []):
        project_id = project.get("id")
        if not project_id:
            continue
        client = (project.get("clientName") or project_id).replace("（线索）", "")
        pipeline = project.get("pipelineColumn") or ""
        arts = [a for a in dashboard.get("artifacts", []) if a.get("projectId") == project_id]

        if role_id == "product":
            has_prd = any((a.get("kind") or "") == "prd" for a in arts)
            if pipeline in {"lead", "clarify", "active"} and not has_prd:
                signals.append(
                    Signal(
                        signal_type="artifact.missing",
                        role_id="product",
                        project_id=project_id,
                        priority="medium",
                        title=f"建议：{client} 可撰写 PRD",
                        preview="项目尚无 PRD 产出",
                        fingerprint=f"artifact.missing:prd:{project_id}",
                        risk_level="low",
                        suggested_action="dispatch",
                        suggested_role="product",
                        suggested_title=f"{client} · 需求 PRD 初稿",
                    )
                )

        if role_id == "legal":
            has_legal = any(
                (a.get("roleId") == "legal")
                or (a.get("kind") or "") in {"nda", "contract", "sow"}
                for a in arts
            )
            if pipeline in {"lead", "clarify"} and not has_legal:
                updated = project.get("updatedAt") or project.get("createdAt")
                stale = True
                if updated:
                    try:
                        ts = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                        stale = now - ts.astimezone(timezone.utc) >= timedelta(days=7)
                    except ValueError:
                        stale = True
                if stale:
                    signals.append(
                        Signal(
                            signal_type="nda.stale",
                            role_id="legal",
                            project_id=project_id,
                            priority="medium",
                            title=f"建议：{client} 法务材料空缺",
                            preview="线索阶段超过 7 天无法务 artifact",
                            fingerprint=f"nda.stale:{project_id}",
                            risk_level="low",
                            suggested_action="dispatch",
                            suggested_role="legal",
                            suggested_title=f"{client} · NDA 起草",
                        )
                    )

        if role_id == "dev":
            has_dev = any(a.get("roleId") == "dev" for a in arts)
            if pipeline in {"active", "clarify"} and not has_dev:
                pending_dev = any(
                    t.get("roleId") == "dev"
                    and t.get("projectId") == project_id
                    and t.get("status") in {"pending", "running", "done"}
                    for t in dashboard.get("tasks", [])
                )
                if not pending_dev:
                    signals.append(
                        Signal(
                            signal_type="build.missing",
                            role_id="dev",
                            project_id=project_id,
                            priority="low",
                            title=f"建议：{client} 可安排技术交付",
                            preview="尚无开发 artifact",
                            fingerprint=f"build.missing:{project_id}",
                            risk_level="low",
                            suggested_action="review",
                        )
                    )

        if role_id == "ops":
            if pipeline == "done" or "阶段5" in (project.get("stage") or ""):
                has_ops = any(a.get("roleId") == "ops" for a in arts)
                if not has_ops:
                    signals.append(
                        Signal(
                            signal_type="deploy.pending",
                            role_id="ops",
                            project_id=project_id,
                            priority="medium",
                            title=f"建议：{client} 结项/运维交付",
                            preview="项目接近完成，尚无运营交付",
                            fingerprint=f"deploy.pending:{project_id}",
                            risk_level="low",
                            suggested_action="dispatch",
                            suggested_role="ops",
                            suggested_title=f"{client} · 结项交付",
                        )
                    )

    return signals


def observe_hitl_pending(dashboard: dict[str, Any]) -> list[Signal]:
    signals: list[Signal] = []
    for project in dashboard.get("projects", []):
        if not project.get("hitlPending"):
            continue
        project_id = project.get("id")
        client = (project.get("clientName") or project_id).replace("（线索）", "")
        signals.append(
            Signal(
                signal_type="hitl.pending",
                role_id="ceo",
                project_id=project_id,
                priority="high",
                title=f"待你审批 · {client}",
                preview=f"HITL {project.get('hitlPending')}",
                fingerprint=f"hitl.pending:{project_id}:{project.get('hitlPending')}",
                risk_level="medium",
                suggested_action="review",
            )
        )
    return signals


def observe_open_questions(dashboard: dict[str, Any]) -> list[Signal]:
    from app.services.project_briefs import get_brief

    signals: list[Signal] = []
    for project in dashboard.get("projects", []):
        project_id = project.get("id")
        if not project_id:
            continue
        brief = get_brief(dashboard, project_id)
        client = (project.get("clientName") or project_id).replace("（线索）", "")
        for idx, question in enumerate(brief.get("openQuestions") or []):
            q = str(question).strip()
            if not q:
                continue
            signals.append(
                Signal(
                    signal_type="brief.open_question",
                    role_id="ceo",
                    project_id=project_id,
                    priority="high",
                    title=f"待 Founder 确认 · {client}",
                    preview=q[:120],
                    fingerprint=f"brief.open_question:{project_id}:{idx}:{q[:40]}",
                    risk_level="medium",
                    suggested_action="review",
                )
            )
    return signals
