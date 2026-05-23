"""Skill chains API — Epic 5."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.api.deps import fail, ok
from app.db import get_session
from app.presentation.skills import sync_skill_catalog
from app.services.dashboard_store import get_dashboard, mutate

router = APIRouter(tags=["skill-chains"])


class ChainStepBody(BaseModel):
    skillId: str
    onFail: str = "halt"


class SkillChainCreate(BaseModel):
    id: str = Field(min_length=2, max_length=48)
    name: str
    steps: list[ChainStepBody]


@router.get("/skill-chains")
def list_skill_chains(session: Session = Depends(get_session)):
    dashboard = get_dashboard(session)
    sync_skill_catalog(dashboard)
    return ok(dashboard.get("skillChains", []))


@router.post("/skill-chains")
def create_skill_chain(body: SkillChainCreate, session: Session = Depends(get_session)):
    with mutate(session) as dashboard:
        sync_skill_catalog(dashboard)
        chains = dashboard.setdefault("skillChains", [])
        if any(c.get("id") == body.id for c in chains):
            raise fail("CHAIN_EXISTS", "Skill 链 ID 已存在", status=409)
        chain = {
            "id": body.id,
            "name": body.name,
            "steps": [s.model_dump() for s in body.steps],
        }
        chains.append(chain)
    return ok(chain)
