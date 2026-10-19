"""전체 파이프라인 조립(Wiring) 및 시나리오 제어."""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from aiops.rag_agent import make_rag_agent
from aiops.remediation import AIOpsEngine, Remediator, SlackNotifier
from config import settings
from edge_simulator.generator import EdgeSimulator, InProcessTransport, WebSocketTransport
from pipeline.dataflow_worker import DataflowWorkerPool, make_sink
from pipeline.gateway import IngestionGateway
from pipeline.message_hub import MessageHub, make_broker
from state import StateStore

log = logging.getLogger("aiops.runtime")


class Platform:
    def __init__(self) -> None:
        self.store = StateStore()
        self.broker = make_broker()
        self.sink = make_sink()
        self.hub = MessageHub(self.store, self.broker)
        self.gateway = IngestionGateway(self.store, self.hub)
        self.pool = DataflowWorkerPool(self.store, self.broker, self.sink)
        self.notifier = SlackNotifier()
        self.remediator = Remediator(self.store, make_rag_agent(), self.notifier, self.pool, self.gateway)
        self.engine = AIOpsEngine(self.store, self.broker, self.remediator, self.pool)
        self.transport = (
            WebSocketTransport(settings.ingest_ws_url)
            if settings.edge_transport == "ws"
            else InProcessTransport(self.gateway)
        )
        self.edge = EdgeSimulator(self.transport)
        self._tasks: list[asyncio.Task] = []
        self._burst: Optional[asyncio.Task] = None

    async def start(self) -> None:
        self.gateway.reset()  # last_seen 초기화
        await self.pool.start()
        for coro in (
            self.hub.monitor(),
            self.gateway.heartbeat_monitor(),
            self.engine.run(),
            self.engine.autoscale_down_loop(),
            self.edge.run(),
        ):
            self._tasks.append(asyncio.create_task(coro))
        log.info("platform started (mode=%s, edge=%s)", settings.mode, settings.edge_transport)

    async def stop(self) -> None:
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        await self.pool.stop()
        if isinstance(self.transport, WebSocketTransport):
            await self.transport.close()

    def rows_written(self) -> int:
        return getattr(self.sink, "count", 0)

    def snapshot(self):
        return self.store.snapshot(rows_written=self.rows_written())

    # ── 시나리오 ────────────────────────────────────────────
    async def apply_scenario(self, sid: int) -> list[int]:
        s = self.store
        if sid == 0:  # Normal — 전체 복구
            if self._burst:
                self._burst.cancel()
            self.edge.reset()
            self.engine.reset()
            self.pool.reset()
            self.hub.reset()
            self.gateway.reset()
            s.active_scenarios.clear()
            s.clear_events()
        elif sid == 1:  # 캡 닫힘 모터 과부하 + 주문 폭증
            s.active_scenarios.add(1)
            self.edge.trigger_motor_fault()
            if self._burst:
                self._burst.cancel()
            self._burst = asyncio.create_task(self.edge.order_burst())
        elif sid == 2:  # 콜드체인 Zone A 온도 상승 + 노드 단절
            s.active_scenarios.add(2)
            self.edge.trigger_zone_a_fault()
        return sorted(s.active_scenarios)
