"""Pulse status and stream endpoints."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from app.api.deps import ok
from app.db import get_session
from app.pulse.coordinator import get_pulse_coordinator
from app.pulse.modules.execution import drain_pending_queue
from app.pulse.signatures import build_stream_payload
from app.services.dashboard_store import get_dashboard
from app.services.runtime_settings import get_runtime_settings, pulse_enabled

router = APIRouter(tags=["pulse"])


@router.get("/pulse/status")
def pulse_status(session: Session = Depends(get_session)):
    dashboard = get_dashboard(session)
    meta = dashboard.get("meta") or {}
    return ok(
        {
            "enabled": pulse_enabled(dashboard),
            "settings": get_runtime_settings(dashboard),
            "runtime": meta.get("pulseRuntime") or {},
        }
    )


@router.post("/pulse/drain")
async def pulse_drain(session: Session = Depends(get_session)):
    ran = await drain_pending_queue(session, max_tasks=24)
    return ok({"drained": ran})


@router.get("/pulse/stream")
async def pulse_stream(session: Session = Depends(get_session)):
    coordinator = get_pulse_coordinator()

    async def event_generator():
        dashboard = get_dashboard(session)
        prev_sig = ""
        queue = coordinator.subscribe_stream()
        try:
            while True:
                dashboard = get_dashboard(session)
                payload = build_stream_payload(session, dashboard)
                sig = json.dumps(payload.get("modules") or {}, sort_keys=True)
                if sig != prev_sig:
                    prev_sig = sig
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                try:
                    queued = await asyncio.wait_for(queue.get(), timeout=1.0)
                    sig = json.dumps(queued.get("modules") or {}, sort_keys=True)
                    if sig != prev_sig:
                        prev_sig = sig
                        yield f"data: {json.dumps(queued, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    pass
        finally:
            coordinator.unsubscribe_stream(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
