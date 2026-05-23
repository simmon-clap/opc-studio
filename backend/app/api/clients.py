"""Client endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.deps import fail, ok
from app.db import get_session
from app.services.dashboard_store import get_dashboard

router = APIRouter(tags=["clients"])


@router.get("/clients")
def list_clients(session: Session = Depends(get_session)):
    dashboard = get_dashboard(session)
    return ok(dashboard.get("clients", []))


@router.get("/clients/{client_id}")
def get_client(client_id: str, session: Session = Depends(get_session)):
    dashboard = get_dashboard(session)
    client = next(
        (c for c in dashboard.get("clients", []) if c.get("id") == client_id),
        None,
    )
    if client is None:
        raise fail("CLIENT_NOT_FOUND", "客户不存在", status=404)

    payments = [
        p for p in dashboard.get("payments", []) if p.get("clientId") == client_id
    ]
    return ok({**client, "payments": payments})
