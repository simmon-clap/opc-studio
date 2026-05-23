"""Orchestrator engine — Phase 3a–3f with real LLM."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlmodel import Session, select

from app.db import session_scope
from app.models.agent_runs import AgentRun
from app.models.deliberation_sessions import DeliberationSession
from app.models.handoffs import Handoff
from app.models.orchestration_events import OrchestrationEvent
from app.services.dispatch_feed import log_accept, log_complete, log_task_failed, set_orchestration_active
from app.orchestrator.ceo_review import review_artifact
from app.orchestrator.ceo_turn import apply_turn_side_effects, run_ceo_turn
from app.orchestrator.supervisor import (
    link_open_commitments_to_task,
    on_task_completed,
    on_task_failed,
    record_workflow_run,
)
from app.orchestrator.dispatch_planner import DispatchPlan, plan_dispatch
from app.orchestrator.directives import RoleDirective
from app.orchestrator import deliberation, dispatcher, transitions
from app.runners.base import RunContext, RunResult
from app.runners.registry import build_task_prompt, run_role
from app.services import aggregates
from app.services.cost_recorder import record_agent_cost
from app.services.dashboard_store import mutate, save
from app.services.ingress_documents import attachment_context_for_prompt
from app.services.llm_client import LlmError
from app.deliverables import build_artifact_record, resolve_deliverable
from app.services.project_store import write_artifact_file, write_artifact_files
from app.services.artifact_versions import append_version, init_version
from app.services.intake_service import process_intake, resolve_project_id
from app.services.dashboard_normalize import normalize_dashboard_domains
from app.services.artifact_workflow import maybe_submit_artifact_review
from app.services.role_config_service import get_role_runtime_config
from app.pulse.modules.execution import drain_pending_queue

MAX_CEO_REVISION_DEPTH = 3

logger = logging.getLogger(__name__)

_orchestrator: "Orchestrator | None" = None


class Orchestrator:
    async def on_event(self, event_type: str, payload: dict[str, Any]) -> None:
        with session_scope() as session:
            self._log_event(session, event_type, payload)
            try:
                if event_type == "ceo.brief":
                    await self._on_ceo_brief(session, payload)
                elif event_type == "hitl.approved":
                    await self._on_hitl_approved(session, payload)
                elif event_type == "hitl.rejected":
                    await self._on_hitl_rejected(session, payload)
                elif event_type == "inbox.resolved":
                    await self._on_inbox_resolved(session, payload)
            except LlmError as exc:
                logger.warning("Orchestrator LLM error: %s", exc.message)
                await self._on_llm_error(session, payload, exc)

    async def _on_llm_error(
        self, session: Session, payload: dict[str, Any], exc: LlmError
    ) -> None:
        with mutate(session) as dashboard:
            self._append_thread_reply(
                dashboard,
                f"⚠️ LLM 调用失败：{exc.message}。请检查设置 → 角色 API 配置 → 测试连接。",
                msg_type="analysis",
            )

    def _log_event(
        self, session: Session, event_type: str, payload: dict[str, Any]
    ) -> None:
        session.add(
            OrchestrationEvent(
                id=f"oe-{uuid4().hex[:10]}",
                project_id=payload.get("projectId"),
                event_type=event_type,
                payload_json=json.dumps(payload, ensure_ascii=False),
                created_at=datetime.now(timezone.utc),
            )
        )
        session.commit()

    async def _on_ceo_brief(self, session: Session, payload: dict[str, Any]) -> None:
        text = payload.get("text", "")
        attachment_ids = payload.get("attachmentIds") or []
        project_id, schedule = await self.run_ceo_turn_phase(
            session, text, payload.get("projectId"), attachment_ids=attachment_ids
        )
        if schedule:
            await self.run_workflow_phase(session, text, project_id)

    async def run_ceo_turn_phase(
        self,
        session: Session,
        text: str,
        project_id: str | None = None,
        *,
        attachment_ids: list[str] | None = None,
    ) -> tuple[str, bool]:
        """Unified CEO turn: reply + brief + commitments + dispatch plan."""
        resolved_project = project_id or "proj-beta"
        attachment_ids = attachment_ids or []

        with mutate(session) as dashboard:
            normalize_dashboard_domains(dashboard)
            resolved_project = resolve_project_id(dashboard, text, resolved_project)
            intake = process_intake(dashboard, text)
            if intake:
                resolved_project = intake["projectId"]
                intake_created = bool(intake.get("created"))
            else:
                intake_created = False

            records = [
                a
                for a in dashboard.get("attachments", [])
                if a.get("id") in attachment_ids
            ]
            att_ctx = attachment_context_for_prompt(records)

            if transitions.is_casual_message(text) and not attachment_ids:
                self._replace_pending_ceo_reply(
                    dashboard,
                    transitions.casual_reply_text(),
                    msg_type="analysis",
                )
                aggregates.recompute_all(dashboard)
                return resolved_project, False

            try:
                turn = await run_ceo_turn(
                    session, dashboard, text, resolved_project, attachment_context=att_ctx
                )
                reply = turn.reply.strip() or "收到。"
                if intake:
                    reply = f"{reply}\n\n📌 {intake['summary']}"
                apply_turn_side_effects(
                    dashboard, turn, source="ceo_turn:web"
                )
                self._replace_pending_ceo_reply(
                    dashboard,
                    reply,
                    msg_type="analysis",
                    content=turn.reply_content,
                )
                self._record_run(
                    session,
                    dashboard,
                    "ceo",
                    turn.project_id,
                    None,
                    RunResult(
                        progress_note=reply[:120],
                        model="ceo-turn" if turn.used_llm else "ceo-turn-rules",
                    ),
                )
                resolved_project = turn.project_id
                meta = dashboard.setdefault("meta", {})
                meta["activeProjectId"] = resolved_project
                meta["_pendingDispatchPlan"] = turn.dispatch_plan.to_dict()
                meta["lastCeoTurn"] = {
                    "at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
                    "projectId": resolved_project,
                    "shouldDispatch": turn.dispatch_plan.should_dispatch,
                    "usedLlm": turn.used_llm,
                }
                schedule = turn.dispatch_plan.should_dispatch or turn.dispatch_plan.mode in {
                    "kickoff",
                    "deliberation",
                }
            except LlmError as exc:
                self._replace_pending_ceo_reply(
                    dashboard, f"⚠️ CEO 分析失败：{exc.message}"
                )
                record_workflow_run(
                    dashboard,
                    project_id=resolved_project,
                    plan=None,
                    status="error",
                    error=exc.message,
                )
                aggregates.recompute_all(dashboard)
                return resolved_project, False

            aggregates.recompute_all(dashboard)
            return resolved_project, schedule

    async def run_chat_phase(
        self,
        session: Session,
        text: str,
        project_id: str | None = None,
    ) -> tuple[str, bool]:
        """Legacy alias → unified CEO turn."""
        return await self.run_ceo_turn_phase(session, text, project_id)

    async def run_plan_and_workflow_phase(
        self, session: Session, text: str, project_id: str
    ) -> None:
        """Legacy alias → execute pending dispatch plan."""
        await self.run_workflow_phase(session, text, project_id)

    async def run_workflow_phase(
        self, session: Session, text: str, project_id: str
    ) -> None:
        with mutate(session) as dashboard:
            normalize_dashboard_domains(dashboard)
            set_orchestration_active(dashboard, True)
            resolved = resolve_project_id(dashboard, text, project_id)
            if resolved != project_id:
                logger.info(
                    "Workflow project corrected: %s -> %s",
                    project_id,
                    resolved,
                )
                project_id = resolved
            plan: DispatchPlan | None = None
            try:
                meta = dashboard.setdefault("meta", {})
                plan_data = meta.pop("_pendingDispatchPlan", None)
                if plan_data:
                    plan = DispatchPlan.from_dict(plan_data)
                else:
                    plan = await plan_dispatch(session, dashboard, text, project_id)

                if plan.mode == "directives" and plan.directives:
                    await self._run_directive_dispatch(
                        session, dashboard, project_id, text, plan.directives
                    )
                elif plan.mode == "deliberation" or (
                    plan.should_dispatch and transitions.is_vague_brief(text)
                ):
                    delib = deliberation.open_session(session, project_id=project_id)
                    await deliberation.run_round_async(session, dashboard, delib)
                    artifact = deliberation.close_session(session, dashboard, delib)
                    dispatcher.dispatch_task(
                        dashboard,
                        role_id="ceo",
                        project_id=project_id,
                        title="根据 Decision Memo 更新立项计划",
                    )
                    self._append_thread_reply(
                        dashboard,
                        f"需求较模糊，已召开会诊（{delib.id}）→ Decision Memo：{artifact['id']}",
                        msg_type="decision",
                    )
                elif plan.mode == "kickoff":
                    await self._run_kickoff_chain(session, dashboard, project_id, text)
                elif plan.directives:
                    await self._run_directive_dispatch(
                        session, dashboard, project_id, text, plan.directives
                    )
                elif plan.should_dispatch:
                    self._append_thread_reply(
                        dashboard,
                        "已理解你的指令，但未解析出可派活的具体任务；请再具体说让谁做什么。",
                        msg_type="decision",
                    )
                record_workflow_run(
                    dashboard,
                    project_id=project_id,
                    plan=plan,
                    status="ok",
                )
            except LlmError as exc:
                self._append_thread_reply(
                    dashboard,
                    f"⚠️ 编排失败：{exc.message}",
                    msg_type="decision",
                )
                record_workflow_run(
                    dashboard,
                    project_id=project_id,
                    plan=plan,
                    status="error",
                    error=exc.message,
                )
            aggregates.recompute_all(dashboard)
            await drain_pending_queue(session, max_tasks=24)
            set_orchestration_active(dashboard, False)

    async def _run_kickoff_chain(
        self,
        session: Session,
        dashboard: dict[str, Any],
        project_id: str,
        brief_text: str,
    ) -> None:
        project = next(
            (p for p in dashboard.get("projects", []) if p.get("id") == project_id),
            {},
        )
        client_name = (project.get("clientName") or project_id).replace("（线索）", "")
        project["pipelineColumn"] = "clarify"
        project["stage"] = "阶段2 · 评估立项"
        project["progress"] = max(int(project.get("progress") or 0), 18)

        ceo_task = dispatcher.dispatch_task(
            dashboard,
            role_id="ceo",
            project_id=project_id,
            title=f"{client_name} · 立项评估",
            deliverable_kind="memo",
        )
        product_task = dispatcher.dispatch_task(
            dashboard,
            role_id="product",
            project_id=project_id,
            title=f"{client_name} · 需求 PRD 初稿",
            deliverable_kind="prd",
        )
        save(session, dashboard)
        await drain_pending_queue(session, max_tasks=4)
        with mutate(session) as dashboard:
            project = next(
                (p for p in dashboard.get("projects", []) if p.get("id") == project_id),
                project,
            )
            hitl_id = f"hitl-1-{uuid4().hex[:6]}"
            dashboard.setdefault("hitlQueue", []).insert(
                0,
                {
                    "id": hitl_id,
                    "type": "HITL-1",
                    "projectId": project_id,
                    "title": f"审 {client_name} PRD 与立项范围",
                    "summary": brief_text[:160],
                    "submittedBy": "ceo",
                    "submittedAt": datetime.now(timezone.utc)
                    .astimezone()
                    .isoformat(timespec="seconds"),
                    "artifacts": [],
                },
            )
            project["hitlPending"] = "HITL-1"
            dashboard.setdefault("inbox", []).insert(
                0,
                {
                    "id": f"inbox-{uuid4().hex[:8]}",
                    "category": "approval",
                    "from": "ceo",
                    "channel": "web",
                    "title": f"待批 · {client_name} HITL-1",
                    "preview": "CEO 已完成评估，产品 PRD 初稿待你批准",
                    "projectId": project_id,
                    "hitlId": hitl_id,
                    "at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
                    "read": False,
                    "status": "active",
                },
            )

            self._append_thread_reply(
                dashboard,
                f"已启动 **{client_name}** 编排：CEO 评估 → 产品 PRD → **HITL-1** 待你批准（收件箱 / 项目页可见）。",
                msg_type="decision",
            )

    async def _run_directive_dispatch(
        self,
        session: Session,
        dashboard: dict[str, Any],
        project_id: str,
        brief_text: str,
        directives: list[RoleDirective],
    ) -> None:
        project = next(
            (p for p in dashboard.get("projects", []) if p.get("id") == project_id),
            {},
        )
        client_name = (project.get("clientName") or project_id).replace("（线索）", "")
        lines: list[str] = []
        artifact_refs: list[str] = []

        for directive in directives:
            task_title = f"{client_name} · {directive.title}"
            task = dispatcher.dispatch_task(
                dashboard,
                role_id=directive.role_id,
                project_id=project_id,
                title=task_title,
                deliverable_kind=directive.kind,
            )
            task["briefContext"] = brief_text
            link_open_commitments_to_task(
                dashboard,
                project_id=project_id,
                task_id=task["id"],
                owner_role=directive.role_id,
            )
            aggregates.recompute_all(dashboard)
            save(session, dashboard)
            result = await self._execute_runner(session, dashboard, task, skip_thread=True)
            aggregates.recompute_all(dashboard)
            save(session, dashboard)
            role_label = {
                "legal": "法务",
                "ops": "运营",
                "product": "产品",
                "dev": "开发",
            }.get(directive.role_id, directive.role_id)
            lines.append(f"**{role_label}**：{directive.title}")

            if result and result.artifact_id:
                artifact_refs.append(result.artifact_id)
                art = next(
                    (a for a in dashboard.get("artifacts", []) if a.get("id") == result.artifact_id),
                    None,
                )
                if art and not art.get("hitlId"):
                    dashboard.setdefault("inbox", []).insert(
                        0,
                        {
                            "id": f"inbox-{uuid4().hex[:8]}",
                            "category": "must_read",
                            "from": directive.role_id,
                            "channel": "web",
                            "title": f"{art.get('title', '产出物')} · {client_name}",
                            "preview": (art.get("content") or "")[:80],
                            "projectId": project_id,
                            "artifactId": result.artifact_id,
                            "at": datetime.now(timezone.utc)
                            .astimezone()
                            .isoformat(timespec="seconds"),
                            "read": False,
                            "status": "active",
                        },
                    )

        self._append_thread_reply(
            dashboard,
            f"已派活（{project_id}）：\n"
            + "\n".join(f"- {line}" for line in lines)
            + "\n\n产出物已写入项目工作室，收件箱已通知。",
            msg_type="decision",
        )

    def _replace_pending_ceo_reply(
        self,
        dashboard: dict[str, Any],
        text: str,
        msg_type: str = "analysis",
        content: dict[str, Any] | None = None,
    ) -> None:
        body = (text or "").strip()
        if not body:
            body = "收到。"
        thread = dashboard.get("ceoThread", [])
        for msg in reversed(thread):
            if msg.get("direction") == "ceo_to_founder" and msg.get("type") == "ack":
                msg["type"] = msg_type
                msg["text"] = body
                if content:
                    msg["content"] = content
                msg["at"] = datetime.now(timezone.utc).astimezone().isoformat(
                    timespec="seconds"
                )
                return
        self._append_thread_reply(dashboard, body, msg_type=msg_type, content=content)

    def _append_thread_reply(
        self,
        dashboard: dict[str, Any],
        text: str,
        msg_type: str = "analysis",
        content: dict[str, Any] | None = None,
    ) -> None:
        record: dict[str, Any] = {
            "id": f"thread-{uuid4().hex[:8]}",
            "direction": "ceo_to_founder",
            "channel": "web",
            "type": msg_type,
            "text": text,
            "at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        }
        if content:
            record["content"] = content
        dashboard.setdefault("ceoThread", []).append(record)

    async def _on_hitl_approved(self, session: Session, payload: dict[str, Any]) -> None:
        hitl_id = payload.get("hitlId")
        project_id = payload.get("projectId")
        if not hitl_id or not project_id:
            return

        with mutate(session) as dashboard:
            hitl_item = next(
                (h for h in dashboard.get("hitlQueue", []) if h.get("id") == hitl_id),
                None,
            )
            hitl_type = hitl_item.get("type") if hitl_item else None
            nxt = transitions.next_dispatch_after_hitl(hitl_type or "")
            if nxt:
                role_id, title = nxt
                task = dispatcher.dispatch_task(
                    dashboard,
                    role_id=role_id,
                    project_id=project_id,
                    title=title,
                )
                await self._execute_runner(session, dashboard, task)
            aggregates.recompute_all(dashboard)
            await drain_pending_queue(session, max_tasks=8)

    async def _on_hitl_rejected(self, session: Session, payload: dict[str, Any]) -> None:
        project_id = payload.get("projectId")
        note = payload.get("note") or "需修改后重新提交"
        hitl_id = payload.get("hitlId")
        if not project_id:
            return
        with mutate(session) as dashboard:
            hitl_item = next(
                (h for h in dashboard.get("hitlQueue", []) if h.get("id") == hitl_id),
                None,
            ) if hitl_id else None
            artifact_id = (hitl_item or {}).get("artifactId") or payload.get("artifactId")
            if artifact_id:
                art = next(
                    (a for a in dashboard.get("artifacts", []) if a.get("id") == artifact_id),
                    None,
                )
                if art:
                    art.setdefault("rejectNotes", []).insert(
                        0,
                        {"note": note, "at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"), "by": "founder"},
                    )
                    art["status"] = "revision"
                    role_id = art.get("roleId") or "legal"
                    kind = art.get("kind") or art.get("type") or "nda"
                    task = dispatcher.dispatch_task(
                        dashboard,
                        role_id=role_id,
                        project_id=project_id,
                        title=f"Founder 驳回修订 · {art.get('title', '产出物')}",
                        deliverable_kind=kind,
                    )
                    task["briefContext"] = f"Founder 驳回意见：{note}"
                    await self._execute_runner(session, dashboard, task, skip_thread=True)
                    self._append_thread_reply(
                        dashboard,
                        f"已按你的驳回意见安排 **{role_id}** 修订（{artifact_id}）。",
                        msg_type="decision",
                    )
            else:
                dispatcher.dispatch_task(
                    dashboard,
                    role_id="ceo",
                    project_id=project_id,
                    title="HITL 驳回 · 协调返工",
                )
            from app.services.founder_profile import suggest_profile_delta

            suggest_profile_delta(
                dashboard,
                note=f"Founder 驳回：{note[:100]}",
                source=f"hitl:{hitl_id}",
            )
            aggregates.recompute_all(dashboard)

    async def _on_inbox_resolved(self, session: Session, payload: dict[str, Any]) -> None:
        action = payload.get("action")
        inbox_id = payload.get("inboxId")
        if action != "approve" or not inbox_id:
            return

        with mutate(session) as dashboard:
            item = next(
                (i for i in dashboard.get("inbox", []) if i.get("id") == inbox_id),
                None,
            )
            if not item:
                return

            category = item.get("category")
            if category == "proposal":
                from app.agency.proposal_actions import execute_proposal_dispatch

                task = execute_proposal_dispatch(dashboard, item)
                if task:
                    self._append_thread_reply(
                        dashboard,
                        f"已采纳建议并派活：**{task.get('title', '任务')}** → {task.get('roleId')}",
                        msg_type="decision",
                    )
            elif category == "request":
                task = dispatcher.dispatch_task(
                    dashboard,
                    role_id="dev",
                    project_id=item.get("projectId") or "proj-beta",
                    title="PoC 样本测试（请示已批）",
                )
                await self._execute_runner(session, dashboard, task)

            aggregates.recompute_all(dashboard)

        await drain_pending_queue(session, max_tasks=4)

    def _record_run(
        self,
        session: Session,
        dashboard: dict[str, Any],
        role_id: str,
        project_id: str | None,
        task_id: str | None,
        result,
    ) -> None:
        session.add(
            AgentRun(
                id=f"run-{uuid4().hex[:10]}",
                task_id=task_id,
                role_id=role_id,
                project_id=project_id,
                status="succeeded",
                model=getattr(result, "model", "stub"),
                input_tokens=result.tokens_in,
                output_tokens=result.tokens_out,
                cost_cny=float(result.cost_cny or 0),
                started_at=datetime.now(timezone.utc),
                finished_at=datetime.now(timezone.utc),
            )
        )
        record_agent_cost(
            dashboard,
            role_id=role_id,
            project_id=project_id,
            input_tokens=result.tokens_in,
            output_tokens=result.tokens_out,
            cost_cny=float(result.cost_cny or 0),
            model=getattr(result, "model", "stub"),
        )
        session.commit()

    def _find_regeneratable_artifact(
        self,
        dashboard: dict[str, Any],
        project_id: str,
        kind: str,
        role_id: str,
    ) -> dict[str, Any] | None:
        for art in dashboard.get("artifacts", []):
            if art.get("projectId") != project_id:
                continue
            art_kind = (art.get("kind") or art.get("type") or "").lower()
            title = (art.get("title") or "").lower()
            if art_kind != kind and not (kind == "nda" and "nda" in title):
                continue
            if role_id == "legal" or art.get("roleId") == role_id:
                return art
        return None

    async def _execute_runner(
        self,
        session: Session,
        dashboard: dict[str, Any],
        task: dict[str, Any],
        *,
        skip_thread: bool = False,
    ):
        role_id = task.get("roleId")
        if task.get("status") == "pending":
            dispatcher.claim_task_running(dashboard, task)
        ctx = RunContext(dashboard, task.get("projectId", ""), task)
        log_accept(
            dashboard,
            role_id=role_id or "ceo",
            task=task,
            project_id=ctx.project_id,
        )

        try:
            prompt = build_task_prompt(ctx, brief_text=task.get("briefContext", ""))
            result = await run_role(session, ctx, user_prompt=prompt)
        except LlmError as exc:
            dispatcher.complete_task(dashboard, task["id"], f"失败：{exc.message}")
            log_task_failed(
                dashboard,
                role_id=role_id or "ceo",
                task=task,
                project_id=ctx.project_id,
                reason=exc.message,
            )
            on_task_failed(
                dashboard,
                project_id=ctx.project_id,
                task_id=task["id"],
                owner_role=role_id or "ceo",
                reason=exc.message,
            )
            if not skip_thread and role_id == "ceo":
                self._append_thread_reply(dashboard, f"⚠️ {exc.message}")
            return None

        if result.artifact_id:
            content = (result.artifact_content or "").strip()
            spec = resolve_deliverable(
                role_id,
                task.get("title") or "",
                directive_kind=task.get("deliverableKind"),
                brief_context=task.get("briefContext") or "",
            )
            if not content:
                from app.deliverables.templates import get_template

                content = get_template(spec.template_id).skeleton
            artifact = build_artifact_record(
                artifact_id=result.artifact_id,
                spec=spec,
                content=content,
                role_id=role_id,
                project_id=ctx.project_id,
                task_id=task.get("id"),
                demo_url=getattr(result, "demo_url", None),
                files=getattr(result, "artifact_files", None) or [],
                images=getattr(result, "artifact_images", None) or [],
            )
            if result.artifact_title:
                artifact["title"] = result.artifact_title

            existing = self._find_regeneratable_artifact(
                dashboard, ctx.project_id, spec.kind, role_id
            )
            saved_art: dict[str, Any] | None = None
            if existing:
                artifact_id = existing["id"]
                result.artifact_id = artifact_id
                for key in (
                    "kind",
                    "format",
                    "viewer",
                    "group",
                    "type",
                    "icon",
                    "templateId",
                    "status",
                    "quality",
                    "taskId",
                    "roleId",
                ):
                    if key in artifact:
                        existing[key] = artifact[key]
                if result.artifact_title:
                    existing["title"] = result.artifact_title
                append_version(
                    existing,
                    content,
                    author=role_id,
                    note="重新生成",
                    project_id=ctx.project_id,
                )
                if artifact.get("files"):
                    existing["files"] = artifact["files"]
                    write_artifact_files(ctx.project_id, artifact_id, artifact["files"])
                write_artifact_file(ctx.project_id, artifact_id, content)
                saved_art = existing
            else:
                init_version(artifact, content, author=role_id, project_id=ctx.project_id)
                if artifact.get("files"):
                    write_artifact_files(ctx.project_id, result.artifact_id, artifact["files"])
                dashboard.setdefault("artifacts", []).insert(0, artifact)
                write_artifact_file(ctx.project_id, result.artifact_id, content)
                saved_art = artifact

            review = review_artifact(
                session, dashboard, saved_art, project_id=ctx.project_id
            )
            depth = int(task.get("_revisionDepth") or 0)
            if review.action == "revision" and review.directive and depth < MAX_CEO_REVISION_DEPTH:
                rev_task = dispatcher.dispatch_task(
                    dashboard,
                    role_id=review.directive.role_id,
                    project_id=ctx.project_id,
                    title=review.directive.title,
                    deliverable_kind=review.directive.kind,
                )
                rev_task["briefContext"] = (
                    f"CEO 修订意见（第 {len(saved_art.get('reviewNotes') or [])} 轮）：{review.note}\n\n"
                    f"{task.get('briefContext') or ''}"
                )
                rev_task["_revisionDepth"] = depth + 1
                dispatcher.complete_task(
                    dashboard,
                    task["id"],
                    f"{result.progress_note or '完成'} · CEO 要求修订",
                )
                self._record_run(session, dashboard, role_id, ctx.project_id, task["id"], result)
                save(session, dashboard)
                return await self._execute_runner(
                    session, dashboard, rev_task, skip_thread=skip_thread
                )
            if review.action == "escalate":
                self._append_thread_reply(
                    dashboard,
                    f"⚠️ {review.note}",
                    msg_type="decision",
                )
            elif review.action == "pass" and saved_art:
                maybe_submit_artifact_review(dashboard, saved_art, ctx.project_id)

            project = next(
                (p for p in dashboard.get("projects", []) if p.get("id") == ctx.project_id),
                None,
            )
            if project and role_id:
                assignees = project.setdefault("assignees", [])
                if role_id not in assignees:
                    assignees.append(role_id)

            on_task_completed(dashboard, task["id"], result.artifact_id)
            dispatcher.complete_task(dashboard, task["id"], result.progress_note or "完成")
            log_complete(
                dashboard,
                role_id=role_id or "ceo",
                task=task,
                project_id=ctx.project_id,
                note=result.progress_note or "完成",
            )
            self._record_run(session, dashboard, role_id, ctx.project_id, task["id"], result)
            session.add(
                Handoff(
                    id=f"ho-{uuid4().hex[:10]}",
                    project_id=ctx.project_id,
                    from_role_id=role_id,
                    to_role_id=result.handoff_to,
                    task_id=task["id"],
                    payload_json=json.dumps(
                        {"artifactId": result.artifact_id, "note": result.progress_note},
                        ensure_ascii=False,
                    ),
                    status="pending",
                    created_at=datetime.now(timezone.utc),
                )
            )
            session.commit()
            return result

        dispatcher.complete_task(dashboard, task["id"], result.progress_note or "完成")
        log_complete(
            dashboard,
            role_id=role_id or "ceo",
            task=task,
            project_id=ctx.project_id,
            note=result.progress_note or "完成",
        )
        self._record_run(session, dashboard, role_id, ctx.project_id, task["id"], result)

        session.add(
            Handoff(
                id=f"ho-{uuid4().hex[:10]}",
                project_id=ctx.project_id,
                from_role_id=role_id,
                to_role_id=result.handoff_to,
                task_id=task["id"],
                payload_json=json.dumps(
                    {"artifactId": result.artifact_id, "note": result.progress_note},
                    ensure_ascii=False,
                ),
                status="pending",
                created_at=datetime.now(timezone.utc),
            )
        )
        session.commit()
        return result

    def get_deliberation(self, session: Session, project_id: str) -> dict | None:
        row = session.exec(
            select(DeliberationSession)
            .where(DeliberationSession.project_id == project_id)
            .order_by(DeliberationSession.created_at.desc())
        ).first()
        if not row:
            return None
        return deliberation.serialize_session(session, row)


def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator
