"""Unified SSE — pulse modules + typed events."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from app.db import get_session
from app.pulse.coordinator import get_pulse_coordinator
from app.pulse.signatures import build_stream_payload
from app.services.dashboard_store import get_dashboard

router = APIRouter(tags=["events"])


@router.get("/events")
async def events_stream(session: Session = Depends(get_session)):
    coordinator = get_pulse_coordinator()

    async def event_generator():
        prev_sig = ""
        queue = coordinator.subscribe_stream()
        try:
            while True:
                dashboard = get_dashboard(session)
                payload = build_stream_payload(session, dashboard)
                modules = payload.get("modules") or {}
                sig = json.dumps(modules, sort_keys=True)
                if sig != prev_sig:
                    prev_sig = sig
                    envelope = {
                        "event": "dashboard.patch",
                        "data": {"modules": modules, "pulseRuntime": (dashboard.get("meta") or {}).get("pulseRuntime")},
                    }
                    yield f"event: dashboard.patch\ndata: {json.dumps(envelope, ensure_ascii=False)}\n\n"
                try:
                    queued = await asyncio.wait_for(queue.get(), timeout=1.0)
                    modules = queued.get("modules") or {}
                    sig = json.dumps(modules, sort_keys=True)
                    if sig != prev_sig:
                        prev_sig = sig
                        envelope = {"event": "dashboard.patch", "data": queued}
                        yield f"event: dashboard.patch\ndata: {json.dumps(envelope, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
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
