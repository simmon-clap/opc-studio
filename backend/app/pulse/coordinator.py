"""Pulse coordinator — asyncio loop for L1 modules."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from sqlmodel import Session

from app.agency.runner import tick_agency
from app.db import session_scope
from app.pulse.modules import commitments, delivery, execution, handoff, presentation, reconcile
from app.pulse.signatures import build_stream_payload, execution_signature, stream_signature
from app.services.dashboard_store import get_dashboard, mutate
from app.services.runtime_settings import get_runtime_settings, pulse_enabled

logger = logging.getLogger(__name__)

PulseRunner = Callable[[Session], dict[str, Any] | Awaitable[dict[str, Any]]]

AGENCY_ROLES = ("ceo", "product", "legal", "dev", "ops")


@dataclass
class PulseCoordinator:
    _task: asyncio.Task | None = field(default=None, init=False)
    _last_run: dict[str, float] = field(default_factory=dict, init=False)
    _last_stream_sig: str = field(default="", init=False)
    _last_modules: dict[str, Any] = field(default_factory=dict, init=False)
    _stream_subscribers: list[asyncio.Queue] = field(default_factory=list, init=False)

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._loop(), name="opc-pulse")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _loop(self) -> None:
        await asyncio.sleep(0.5)
        idle_ticks = 0
        while True:
            try:
                busy = await self.tick()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Pulse tick failed")
                busy = False
            if busy:
                idle_ticks = 0
                await asyncio.sleep(1.0)
            else:
                idle_ticks += 1
                await asyncio.sleep(min(5.0, 1.0 + idle_ticks * 0.75))

    def _system_idle(self, dashboard: dict[str, Any]) -> bool:
        exec_sig = execution_signature(dashboard)
        meta = dashboard.get("meta") or {}
        if exec_sig["pending"] > 0 or exec_sig["running"] > 0:
            return False
        if meta.get("orchestrationActive"):
            return False
        return True

    def _interval_multiplier(self, dashboard: dict[str, Any]) -> float:
        exec_sig = execution_signature(dashboard)
        if exec_sig["pending"] > 0 or exec_sig["running"] > 0:
            return 2.0
        return 1.0

    def _should_run(
        self,
        module_id: str,
        interval_sec: float,
        dashboard: dict[str, Any],
        *,
        apply_exec_idle: bool = False,
        apply_load_multiplier: bool = False,
    ) -> bool:
        import time

        if not pulse_enabled(dashboard):
            return False

        settings = get_runtime_settings(dashboard)
        exec_sig = execution_signature(dashboard)
        if apply_exec_idle and module_id == "execution":
            if exec_sig["pending"] == 0 and exec_sig["running"] == 0:
                interval_sec = float(
                    settings.get("pulse", {}).get("executionIdleIntervalSec") or 60
                )
        if apply_load_multiplier:
            interval_sec *= self._interval_multiplier(dashboard)

        now = time.monotonic()
        last = self._last_run.get(module_id, 0.0)
        if now - last < interval_sec:
            return False
        self._last_run[module_id] = now
        return True

    async def tick(self) -> bool:
        ran_work = False
        with session_scope() as session:
            dashboard = get_dashboard(session)
            if not pulse_enabled(dashboard):
                return False
            settings = get_runtime_settings(dashboard)
            pulse_cfg = settings.get("pulse", {})
            agency_cfg = settings.get("agency", {})
            idle = self._system_idle(dashboard)

            pres_interval = float(pulse_cfg.get("presentationIntervalSec") or 2)
            if idle:
                pres_interval = float(pulse_cfg.get("presentationIdleIntervalSec") or 10)

            if self._should_run(
                "presentation",
                pres_interval,
                dashboard,
            ):
                presentation.tick_presentation(session)
                ran_work = True

            if self._should_run(
                "reconcile",
                float(pulse_cfg.get("reconcileIntervalSec") or 120),
                dashboard,
            ):
                reconcile.tick_reconcile(session)
                ran_work = True

            if self._should_run(
                "handoff",
                float(pulse_cfg.get("handoffIntervalSec") or 10),
                dashboard,
            ):
                result = handoff.tick_handoff(session)
                ran_work = ran_work or bool(result.get("consumed"))

            if self._should_run(
                "delivery",
                float(pulse_cfg.get("deliveryIntervalSec") or 30),
                dashboard,
            ):
                delivery.tick_delivery(session)
                ran_work = True

            if self._should_run(
                "commitments",
                float(pulse_cfg.get("commitmentsIntervalSec") or 3600),
                dashboard,
            ):
                commitments.tick_commitments(session)
                ran_work = True

            exec_interval = float(pulse_cfg.get("executionIntervalSec") or 5)
            if self._should_run(
                "execution",
                exec_interval,
                dashboard,
                apply_exec_idle=True,
            ):
                await execution.tick_execution(session)
                ran_work = True

            if agency_cfg.get("enabled"):
                ceo_interval = float(agency_cfg.get("ceoObserveIntervalSec") or 300)
                role_interval = float(agency_cfg.get("roleObserveIntervalSec") or 120)
                for role in AGENCY_ROLES:
                    module_id = f"agency.{role}"
                    interval = ceo_interval if role == "ceo" else role_interval
                    if self._should_run(
                        module_id,
                        interval,
                        dashboard,
                        apply_load_multiplier=True,
                    ):
                        await tick_agency(session, role_id=role)
                        ran_work = True

            self._publish_stream(session)
            if not idle:
                self._write_runtime_heartbeat(session)
        return ran_work

    def _write_runtime_heartbeat(self, session: Session) -> None:
        now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        with mutate(session) as dashboard:
            meta = dashboard.setdefault("meta", {})
            runtime = meta.setdefault("pulseRuntime", {})
            runtime["lastTickAt"] = now
            runtime["paused"] = not pulse_enabled(dashboard)

    def _publish_stream(self, session: Session) -> None:
        dashboard = get_dashboard(session)
        payload = build_stream_payload(
            session, dashboard, prev_modules=self._last_modules or None
        )
        sig = stream_signature(payload)
        if sig == self._last_stream_sig:
            return
        self._last_stream_sig = sig
        self._last_modules = payload.get("modules") or {}
        for queue in list(self._stream_subscribers):
            if queue.full():
                continue
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                pass

    def subscribe_stream(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=8)
        self._stream_subscribers.append(queue)
        return queue

    def unsubscribe_stream(self, queue: asyncio.Queue) -> None:
        if queue in self._stream_subscribers:
            self._stream_subscribers.remove(queue)


_coordinator: PulseCoordinator | None = None


def get_pulse_coordinator() -> PulseCoordinator:
    global _coordinator
    if _coordinator is None:
        _coordinator = PulseCoordinator()
    return _coordinator


async def start_pulse_loop() -> None:
    await get_pulse_coordinator().start()


async def drain_pending_queue(session: Session, *, max_tasks: int = 20) -> int:
    return await execution.drain_pending_queue(session, max_tasks=max_tasks)
