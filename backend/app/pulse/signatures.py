"""Compute stream signatures for pulse modules."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlmodel import Session, select

from app.models.handoffs import Handoff
from app.services.dispatch_feed import feed_signature


def _hash_payload(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def execution_signature(dashboard: dict[str, Any]) -> dict[str, Any]:
    tasks = dashboard.get("tasks") or []
    pending = sum(1 for t in tasks if t.get("status") == "pending")
    running = sum(1 for t in tasks if t.get("status") == "running")
    failed = sum(1 for t in tasks if t.get("status") == "failed")
    payload = {
        "pending": pending,
        "running": running,
        "failed": failed,
        "active": pending > 0 or running > 0,
    }
    payload["sig"] = _hash_payload(payload)
    return payload


def inbox_signature(dashboard: dict[str, Any]) -> dict[str, Any]:
    inbox = dashboard.get("inbox") or []
    active = [i for i in inbox if i.get("status") == "active"]
    proposals = [i for i in active if i.get("category") == "proposal"]
    unread = sum(1 for i in active if not i.get("read"))
    payload = {
        "unread": unread,
        "active": len(active),
        "proposals": len(proposals),
    }
    payload["sig"] = _hash_payload(payload)
    return payload


def presentation_signature(dashboard: dict[str, Any]) -> dict[str, Any]:
    overview = dashboard.get("overviewLive") or dashboard.get("presentation", {}).get("overview")
    projects_sig = _hash_payload(
        [
            {
                "id": p.get("id"),
                "progress": p.get("progress"),
                "stage": p.get("stage"),
                "hitl": p.get("hitlPending"),
            }
            for p in dashboard.get("projects") or []
        ]
    )
    payload = {
        "feedSig": feed_signature(dashboard),
        "overviewLen": len(overview or []),
        "overviewSig": _hash_payload(overview or []),
        "projectsSig": projects_sig,
    }
    payload["sig"] = _hash_payload(payload)
    return payload


def agency_signature(dashboard: dict[str, Any]) -> dict[str, Any]:
    meta = dashboard.get("meta") or {}
    agency_rt = (meta.get("pulseRuntime") or {}).get("agency") or {}
    payload = {
        "lastObserveAt": agency_rt.get("lastObserveAt"),
        "created": (agency_rt.get("lastResult") or {}).get("created", 0),
    }
    payload["sig"] = _hash_payload(payload)
    return payload


def handoff_signature(session: Session) -> dict[str, Any]:
    pending = len(
        session.exec(select(Handoff).where(Handoff.status == "pending")).all()
    )
    payload = {"pending": pending}
    payload["sig"] = _hash_payload(payload)
    return payload


def stream_signature(payload: dict[str, Any]) -> str:
    return _hash_payload(payload.get("modules") or {})


def build_stream_payload(
    session: Session,
    dashboard: dict[str, Any],
    *,
    prev_modules: dict[str, Any] | None = None,
) -> dict[str, Any]:
    meta = dashboard.get("meta") or {}
    exec_sig = execution_signature(dashboard)
    pres_sig = presentation_signature(dashboard)
    inbox_sig = inbox_signature(dashboard)
    agency_sig = agency_signature(dashboard)
    hand_sig = handoff_signature(session)
    runtime = meta.get("pulseRuntime") or {}

    if prev_modules:
        pres_sig["changed"] = pres_sig["sig"] != (prev_modules.get("presentation") or {}).get(
            "sig"
        )
        inbox_sig["changed"] = inbox_sig["sig"] != (prev_modules.get("inbox") or {}).get("sig")
        agency_sig["changed"] = agency_sig["sig"] != (prev_modules.get("agency") or {}).get("sig")
        exec_sig["changed"] = exec_sig["sig"] != (prev_modules.get("execution") or {}).get("sig")
    else:
        pres_sig["changed"] = True
        inbox_sig["changed"] = True
        agency_sig["changed"] = True
        exec_sig["changed"] = True

    return {
        "v": 1,
        "at": meta.get("updatedAt"),
        "modules": {
            "execution": exec_sig,
            "presentation": pres_sig,
            "inbox": inbox_sig,
            "agency": agency_sig,
            "handoff": hand_sig,
            "orchestration": {
                "feedCount": len(dashboard.get("dispatchFeed") or []),
                "active": bool(meta.get("orchestrationActive")),
                "sig": feed_signature(dashboard),
            },
            "runtime": {
                "paused": bool(runtime.get("paused")),
                "sig": _hash_payload({"lastTickAt": runtime.get("lastTickAt")}),
            },
        },
    }
