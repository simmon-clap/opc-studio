"""Deliberation API."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session

from app.api.deps import fail, ok
from app.db import get_session
from app.orchestrator.engine import get_orchestrator

router = APIRouter(tags=["deliberation"])


class FounderNoteBody(BaseModel):
    text: str


@router.get("/projects/{project_id}/deliberation")
def get_project_deliberation(
    project_id: str, session: Session = Depends(get_session)
):
    data = get_orchestrator().get_deliberation(session, project_id)
    if data is None:
        return ok(None)
    return ok(data)


@router.post("/projects/{project_id}/deliberation/{session_id}/founder-note")
def post_founder_note(
    project_id: str,
    session_id: str,
    body: FounderNoteBody,
    session: Session = Depends(get_session),
):
    from datetime import datetime, timezone
    from uuid import uuid4

    from sqlmodel import select

    from app.models.deliberation_sessions import DeliberationSession
    from app.models.deliberation_turns import DeliberationTurn

    text = body.text.strip()
    if not text:
        raise fail("INVALID_NOTE", "内容不能为空")

    delib = session.get(DeliberationSession, session_id)
    if delib is None or delib.project_id != project_id:
        raise fail("DELIB_NOT_FOUND", "会诊不存在", status=404)
    if delib.status != "open":
        raise fail("DELIB_CLOSED", "会诊已关闭", status=409)

    turns = session.exec(
        select(DeliberationTurn).where(DeliberationTurn.session_id == session_id)
    ).all()
    max_idx = max((t.turn_index for t in turns), default=0)

    turn = DeliberationTurn(
        id=f"turn-{uuid4().hex[:8]}",
        session_id=session_id,
        role_id="founder",
        turn_index=max_idx + 1,
        content=text[:1000],
        created_at=datetime.now(timezone.utc),
    )
    session.add(turn)
    session.commit()
    return ok({"id": turn.id, "author": "founder", "content": turn.content})
