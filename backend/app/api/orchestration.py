"""Orchestration live stream for overview."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from app.db import get_session
from app.services.dashboard_store import get_dashboard
from app.services.dispatch_feed import feed_signature

router = APIRouter(tags=["orchestration"])


@router.get("/orchestration/stream")
async def orchestration_stream(session: Session = Depends(get_session)):
    async def event_generator():
        prev_sig = ""
        while True:
            dashboard = get_dashboard(session)
            sig = feed_signature(dashboard)
            if sig != prev_sig:
                prev_sig = sig
                meta = dashboard.get("meta") or {}
                payload = {
                    "feedCount": len(dashboard.get("dispatchFeed") or []),
                    "orchestrationActive": bool(meta.get("orchestrationActive")),
                }
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
