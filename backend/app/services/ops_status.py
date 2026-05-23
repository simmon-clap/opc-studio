"""Operational status summaries — structured blocks for CEO replies."""

from __future__ import annotations

import re
from typing import Any

from app.presentation.blocks import (
    bullet_list,
    callout,
    heading,
    message_content,
    paragraph,
    task_row,
)
from app.presentation.overview import MAX_DIALOGUES, _count_eligible_dialogues
from app.presentation.roles import role_label

STATUS_QUERY_PATTERNS = (
    r"哪些任务",
    r"什么任务",
    r"有啥任务",
    r"有哪些.*进行",
    r"进行中的",
    r"现在在做什么",
    r"在做什么",
    r"在忙什么",
    r"进度怎么样",
    r"当前进度",
    r"任务情况",
    r"工作状态",
    r"团队在做什么",
    r"都在忙",
)


def is_status_query(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    return any(re.search(p, t) for p in STATUS_QUERY_PATTERNS)


def _project_label(dashboard: dict[str, Any], project_id: str) -> str:
    project = next(
        (p for p in dashboard.get("projects", []) if p.get("id") == project_id),
        {},
    )
    name = (project.get("clientName") or project_id or "").replace("（线索）", "")
    return name or project_id


def _short_title(title: str) -> str:
    text = (title or "").strip()
    if " · " in text:
        return text.split(" · ", 1)[-1].strip()
    return text[:80] or "任务"


def summarize_active_work_blocks(dashboard: dict[str, Any]) -> list[dict[str, Any]]:
    """Structured blocks for task status queries."""
    tasks = dashboard.get("tasks") or []
    active = [
        t
        for t in tasks
        if t.get("status") in {"running", "pending"} and t.get("roleId") != "ceo"
    ]
    running = [t for t in active if t.get("status") == "running"]
    pending = [t for t in active if t.get("status") == "pending"]
    blocks: list[dict[str, Any]] = []

    if not active:
        done_recent = [
            t
            for t in tasks
            if t.get("status") == "done" and t.get("roleId") != "ceo"
        ][:3]
        if done_recent:
            blocks.append(paragraph("目前没有进行中的 Agent 任务。最近完成的有："))
            blocks.append(
                bullet_list(
                    [
                        f"{role_label(dashboard, t.get('roleId', ''))} · "
                        f"{_short_title(t.get('title') or '任务')}"
                        f"（{_project_label(dashboard, t.get('projectId', ''))}）"
                        for t in done_recent
                    ]
                )
            )
            blocks.append(callout("需要我继续派活或跟进某个项目，直接说即可。"))
            return blocks
        blocks.append(paragraph("目前没有进行中的任务。你可以告诉我让谁做什么，我会马上派活。"))
        return blocks

    intro = f"我查了一下，现在有 {len(running)} 个任务在执行"
    if pending:
        intro += f"、{len(pending)} 个排队"
    intro += "："
    blocks.append(paragraph(intro))

    by_project: dict[str, list[dict[str, Any]]] = {}
    for task in sorted(
        active, key=lambda t: (0 if t.get("status") == "running" else 1, t.get("startedAt") or "")
    ):
        pid = task.get("projectId") or "unknown"
        by_project.setdefault(pid, []).append(task)

    for project_id, project_tasks in by_project.items():
        label = _project_label(dashboard, project_id)
        blocks.append(heading(label))
        for task in project_tasks:
            status_word = "执行中" if task.get("status") == "running" else "排队"
            blocks.append(
                task_row(
                    role=role_label(dashboard, task.get("roleId", "")),
                    title=_short_title(task.get("title") or "任务"),
                    status=status_word,
                    project=label,
                    project_id=project_id,
                    task_id=task.get("id") or "",
                )
            )

    if (dashboard.get("meta") or {}).get("orchestrationActive"):
        blocks.append(callout("CEO 编排仍在后台进行，完成后我会在对话里补充结果。", tone="info"))

    eligible = _count_eligible_dialogues(dashboard)
    hidden = max(0, eligible - MAX_DIALOGUES)
    if hidden > 0:
        blocks.append(
            callout(
                f"概览图最多同时显示 {MAX_DIALOGUES} 条对话，"
                f"另有 {hidden} 个角色在任务中（点头像可看详情）。",
                tone="muted",
            )
        )

    blocks.append(callout("要调整优先级或加派任务，直接跟我说。", tone="muted"))
    return blocks


def summarize_active_work_content(dashboard: dict[str, Any]) -> dict[str, Any]:
    return message_content(summarize_active_work_blocks(dashboard))


def summarize_active_work(dashboard: dict[str, Any]) -> str:
    """Plain-text fallback for prompts and legacy clients."""
    return summarize_active_work_content(dashboard)["text"]
