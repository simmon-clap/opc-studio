"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import (
    artifacts,
    ceo,
    clients,
    commitments,
    dashboard,
    deliberation,
    finance,
    founder,
    health,
    hitl,
    inbox,
    orchestration,
    pulse,
    project_workflow,
    projects,
    roles,
    runtime,
    settings,
    skills,
    skill_chains,
    mcp,
    tools,
    agent_runs,
    weekly,
)
from app.config import APP_VERSION, PROJECT_ROOT
from app.db import init_db, session_scope
from app.pulse.coordinator import get_pulse_coordinator, start_pulse_loop
from app.pulse.modules.reconcile import tick_reconcile
from app.seed import seed_if_needed
from app.services.dashboard_store import mutate
from app.services.inbox_dedup import dedupe_active_inbox


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    from app.tools.registry import bootstrap_tools

    bootstrap_tools()
    with session_scope() as session:
        seed_if_needed(session)
        tick_reconcile(session)
        with mutate(session) as dashboard:
            dedupe_active_inbox(dashboard)
    await start_pulse_loop()
    yield
    await get_pulse_coordinator().stop()


app = FastAPI(title="OPC Studio API", version=APP_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and "ok" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "ok": False,
            "error": {"code": "HTTP_ERROR", "message": str(exc.detail), "details": {}},
        },
    )


for module in (
    health,
    dashboard,
    projects,
    project_workflow,
    clients,
    artifacts,
    inbox,
    hitl,
    ceo,
    commitments,
    founder,
    weekly,
    finance,
    roles,
    settings,
    skills,
    skill_chains,
    mcp,
    tools,
    agent_runs,
    deliberation,
    orchestration,
    pulse,
    runtime,
):
    app.include_router(module.router, prefix="/api/v1")

# Static assets from project root
if (PROJECT_ROOT / "dashboards" / "app").exists():
    app.mount(
        "/dashboards/app",
        StaticFiles(directory=str(PROJECT_ROOT / "dashboards" / "app"), html=True),
        name="dashboards",
    )

if (PROJECT_ROOT / "assets").exists():
    app.mount(
        "/assets",
        StaticFiles(directory=str(PROJECT_ROOT / "assets")),
        name="assets",
    )

if (PROJECT_ROOT / "architecture.html").exists():

    @app.get("/architecture.html", include_in_schema=False)
    async def architecture_page():
        return FileResponse(PROJECT_ROOT / "architecture.html")


@app.get("/")
async def root():
    return {
        "ok": True,
        "message": "OPC Studio API",
        "dashboard": "/dashboards/app/",
        "docs": "/docs",
    }
