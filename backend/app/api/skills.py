"""Skill Hub API."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session

from app.api.deps import fail, ok
from app.db import get_session
from app.presentation.skills import (
    activate_skill,
    get_skill,
    import_skill,
    sync_skill_catalog,
)
from app.services.dashboard_store import get_dashboard, mutate

router = APIRouter(tags=["skills"])


class SkillImportBody(BaseModel):
    markdown: str


class SkillStatusBody(BaseModel):
    status: str


@router.get("/skills")
def list_skills(session: Session = Depends(get_session)):
    dashboard = get_dashboard(session)
    sync_skill_catalog(dashboard)
    return ok(dashboard.get("skillCatalog", []))


@router.get("/skills/{skill_id}")
def read_skill(skill_id: str, session: Session = Depends(get_session)):
    dashboard = get_dashboard(session)
    skill = get_skill(dashboard, skill_id)
    if skill is None:
        raise fail("SKILL_NOT_FOUND", "Skill 不存在", status=404)
    return ok(skill)


@router.post("/skills/import")
def post_skill_import(body: SkillImportBody, session: Session = Depends(get_session)):
    try:
        with mutate(session) as dashboard:
            skill = import_skill(dashboard, body.markdown)
    except ValueError as exc:
        code = str(exc)
        if code == "SKILL_EXISTS":
            raise fail("SKILL_EXISTS", "Skill ID 已存在", status=409) from exc
        if code == "BUILTIN_PROTECTED":
            raise fail("BUILTIN_PROTECTED", "不可覆盖内置 Skill", status=403) from exc
        if code.startswith("UNKNOWN_TOOL"):
            raise fail("UNKNOWN_TOOL", code, status=400) from exc
        raise fail("INVALID_SKILL", "SKILL.md 格式无效", status=400) from exc
    return ok(skill)


@router.post("/skills/{skill_id}/activate")
def post_skill_activate(skill_id: str, session: Session = Depends(get_session)):
    with mutate(session) as dashboard:
        skill = activate_skill(dashboard, skill_id)
    if skill is None:
        raise fail("SKILL_NOT_FOUND", "Skill 不存在", status=404)
    return ok(skill)


@router.patch("/skills/{skill_id}")
def patch_skill(skill_id: str, body: SkillStatusBody, session: Session = Depends(get_session)):
    with mutate(session) as dashboard:
        skill = get_skill(dashboard, skill_id)
        if skill is None:
            raise fail("SKILL_NOT_FOUND", "Skill 不存在", status=404)
        if skill.get("maintainer") == "builtin" and body.status == "deprecated":
            skill["status"] = "deprecated"
        elif skill.get("maintainer") != "builtin":
            skill["status"] = body.status
    return ok(skill)
