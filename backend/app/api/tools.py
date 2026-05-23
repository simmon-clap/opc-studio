"""Tool registry API."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.deps import ok
from app.db import get_session
from app.services.dashboard_store import get_dashboard
from app.tools.registry import bootstrap_tools, list_tools, resolve_allowed_tools

router = APIRouter(tags=["tools"])


@router.get("/tools")
def get_tools_registry(session: Session = Depends(get_session)):
    bootstrap_tools()
    dashboard = get_dashboard(session)
    items = []
    for spec in list_tools():
        items.append(
            {
                "id": spec.id,
                "name": spec.name,
                "description": spec.description,
                "parametersSchema": spec.parameters_schema,
                "rolesDefault": sorted(spec.roles_default) if spec.roles_default else None,
            }
        )
    return ok(items)


@router.get("/tools/effective/{role_id}")
def get_effective_tools(role_id: str, session: Session = Depends(get_session)):
    bootstrap_tools()
    dashboard = get_dashboard(session)
    allowed = resolve_allowed_tools(dashboard, role_id)
    return ok({"roleId": role_id, "allowedTools": allowed})
