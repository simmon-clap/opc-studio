"""Structured message blocks — CEO thread, status replies, future inbox digests."""

from __future__ import annotations

from typing import Any

from app.presentation.schema import (
    BLOCK_CALLOUT,
    BLOCK_HEADING,
    BLOCK_LIST,
    BLOCK_PARAGRAPH,
    BLOCK_TASK_ROW,
    PRESENTATION_VERSION,
)


def paragraph(text: str) -> dict[str, Any]:
    return {"type": BLOCK_PARAGRAPH, "text": text}


def heading(text: str, *, level: int = 2) -> dict[str, Any]:
    return {"type": BLOCK_HEADING, "level": level, "text": text}


def bullet_list(items: list[str]) -> dict[str, Any]:
    return {"type": BLOCK_LIST, "style": "bullet", "items": items}


def callout(text: str, *, tone: str = "info") -> dict[str, Any]:
    return {"type": BLOCK_CALLOUT, "tone": tone, "text": text}


def task_row(
    *,
    role: str,
    title: str,
    status: str,
    project: str = "",
    project_id: str = "",
    task_id: str = "",
) -> dict[str, Any]:
    return {
        "type": BLOCK_TASK_ROW,
        "role": role,
        "title": title,
        "status": status,
        "project": project,
        "projectId": project_id,
        "taskId": task_id,
    }


def message_content(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    """Envelope stored on ceoThread messages and API payloads."""
    text = blocks_to_plain_text(blocks)
    return {"version": PRESENTATION_VERSION, "text": text, "blocks": blocks}


def blocks_to_plain_text(blocks: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for block in blocks:
        btype = block.get("type")
        if btype == BLOCK_PARAGRAPH:
            parts.append(str(block.get("text") or ""))
        elif btype == BLOCK_HEADING:
            parts.append(str(block.get("text") or ""))
        elif btype == BLOCK_LIST:
            for item in block.get("items") or []:
                parts.append(f"- {item}")
        elif btype == BLOCK_CALLOUT:
            parts.append(str(block.get("text") or ""))
        elif btype == BLOCK_TASK_ROW:
            status = block.get("status") or ""
            parts.append(
                f"- {block.get('role', '')} · {block.get('title', '')}（{status}）"
            )
        parts.append("")
    return "\n".join(p for p in parts if p).strip()
