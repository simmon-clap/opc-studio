"""Deliberation with optional LLM turns."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlmodel import Session, select

from app.models.deliberation_sessions import DeliberationSession
from app.models.deliberation_turns import DeliberationTurn
from app.runners.base import RunContext
from app.runners.registry import run_role
from app.services.project_store import write_artifact_file

DEFAULT_AGENDA = [
    "客户真实需求边界是什么？",
    "应先 PoC 还是直接全量报价？",
    "法务/合规有无红线？",
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _session_meta(
    agenda: list[str] | None, participants: list[str] | None
) -> str:
    return json.dumps(
        {
            "agenda": agenda or DEFAULT_AGENDA,
            "participants": participants or ["product", "legal"],
            "openedBy": "ceo",
            "maxRounds": 2,
            "currentRound": 1,
        },
        ensure_ascii=False,
    )


def open_session(
    session: Session,
    *,
    project_id: str,
    agenda: list[str] | None = None,
    participants: list[str] | None = None,
) -> DeliberationSession:
    sid = f"delib-{uuid4().hex[:8]}"
    row = DeliberationSession(
        id=sid,
        project_id=project_id,
        topic=_session_meta(agenda, participants),
        status="open",
        created_at=_now(),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


async def run_round_async(
    session: Session,
    dashboard: dict[str, Any],
    delib: DeliberationSession,
) -> list[DeliberationTurn]:
    meta = json.loads(delib.topic or "{}")
    agenda = meta.get("agenda", DEFAULT_AGENDA)
    participants = meta.get("participants", ["product", "legal"])
    round_num = meta.get("currentRound", 1)
    turns: list[DeliberationTurn] = []

    ceo_open = DeliberationTurn(
        id=f"turn-{uuid4().hex[:8]}",
        session_id=delib.id,
        role_id="ceo",
        turn_index=round_num * 10,
        content=f"会诊议题：{'；'.join(agenda)}",
        created_at=_now(),
    )
    session.add(ceo_open)
    turns.append(ceo_open)

    idx = 1
    for role_id in participants:
        fake_task = {
            "id": f"delib-task-{role_id}",
            "roleId": role_id,
            "title": "会诊发言",
        }
        ctx = RunContext(dashboard, delib.project_id, fake_task)
        prompt = (
            f"CEO 会诊议题：{'；'.join(agenda)}\n"
            f"项目：{delib.project_id}\n"
            "请从你的角色角度给出简洁意见（200字内）。"
        )
        try:
            result = await run_role(session, ctx, user_prompt=prompt)
            content = (result.progress_note or result.artifact_content or "已发表意见")[:500]
        except Exception as exc:  # noqa: BLE001
            content = f"（{role_id} 发言失败：{exc}）"
        turn = DeliberationTurn(
            id=f"turn-{uuid4().hex[:8]}",
            session_id=delib.id,
            role_id=role_id,
            turn_index=round_num * 10 + idx,
            content=content,
            created_at=_now(),
        )
        session.add(turn)
        turns.append(turn)
        idx += 1

    session.commit()
    return turns


def close_session(
    session: Session,
    dashboard: dict[str, Any],
    delib: DeliberationSession,
) -> dict[str, Any]:
    art_id = f"art-decision-{uuid4().hex[:6]}"
    content = (
        f"# Decision Memo · {delib.project_id}\n\n"
        f"会诊 ID: {delib.id}\n\n"
        f"## 结论\n"
        f"需求边界已对齐，建议 CEO 继续 Dispatch 正式 Task。\n"
    )
    artifact = {
        "id": art_id,
        "projectId": delib.project_id,
        "type": "memo",
        "icon": "doc",
        "title": "Decision Memo",
        "version": "1.0",
        "roleId": "ceo",
        "updatedAt": _now().astimezone().isoformat(timespec="seconds"),
        "content": content,
    }
    dashboard.setdefault("artifacts", []).insert(0, artifact)
    write_artifact_file(delib.project_id, art_id, content)

    delib.status = "closed"
    delib.decision_json = json.dumps({"artifactId": art_id}, ensure_ascii=False)
    delib.closed_at = _now()
    session.add(delib)
    session.commit()
    return artifact


def serialize_session(session: Session, delib: DeliberationSession) -> dict[str, Any]:
    meta = json.loads(delib.topic or "{}")
    decision = json.loads(delib.decision_json or "{}") if delib.decision_json else {}
    turns = session.exec(
        select(DeliberationTurn)
        .where(DeliberationTurn.session_id == delib.id)
        .order_by(DeliberationTurn.turn_index)
    ).all()
    return {
        "id": delib.id,
        "projectId": delib.project_id,
        "status": delib.status,
        "agenda": meta.get("agenda", []),
        "participants": meta.get("participants", []),
        "maxRounds": meta.get("maxRounds", 2),
        "currentRound": meta.get("currentRound", 1),
        "decisionArtifactId": decision.get("artifactId"),
        "turns": [
            {
                "id": t.id,
                "round": t.turn_index // 10,
                "author": t.role_id,
                "content": t.content,
                "at": t.created_at.astimezone().isoformat(timespec="seconds")
                if t.created_at
                else None,
            }
            for t in turns
        ],
    }
