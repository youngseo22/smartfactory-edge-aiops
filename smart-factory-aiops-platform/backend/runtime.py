"""전체 파이프라인 조립(Wiring) 및 시나리오 제어."""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from aiops.rag_agent import make_rag_agent
from aiops.remediation import AIOpsEngine, Remediator, SlackNotifier
from config import TOPIC_ALERT, settings
from edge_simulator.generator import EdgeSimulator, InProcessTransport, WebSocketTransport
from models.schemas import AlertEvent, epoch_ms
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
        elif sid == 1:  # 모터 불량 (단독)
            s.active_scenarios.add(1)
            self.edge.trigger_motor_fault()
            s.motor.svm = settings.svm_fault
            s.motor.status = "WARNING"
            s.push_event("VIBRATION_HIGH")
            ev = AlertEvent(type="VIBRATION_HIGH", source="MOTOR_LINE_A_01", value=settings.svm_fault, threshold=settings.svm_threshold)
            await self.engine.dispatch_now(ev)
            self.hub.emit_alert(ev)
        elif sid == 2:  # 콜드체인 Zone A 온도 상승 + 노드 단절
            s.active_scenarios.add(2)
            self.edge.trigger_zone_a_fault()
        elif sid == 3:  # 주문 폭증 (단독 — 큐 적체 & HPA 오토스케일아웃)
            s.active_scenarios.add(3)
            if self._burst:
                self._burst.cancel()
            self._burst = asyncio.create_task(self.edge.order_burst())
        elif sid == 4:  # 모터 교체 / 현장 정비 완료 (모터 진동 정상화)
            s.active_scenarios.discard(1)
            self.edge.reset_motor()
            s.motor.svm = settings.svm_normal
            s.motor.status = "NORMAL"
            if s.remediation.slack and ("모터" in s.remediation.slack.manual_title or "BEARING" in s.remediation.slack.cause):
                s.remediation.slack = None
            s.remove_events("VIBRATION_HIGH", "ACTION_SLACK")
        elif sid == 5:  # Zone A 센서 및 냉각기 복구 (Failback)
            s.active_scenarios.discard(2)
            self.edge.reset_zone_a()
            self.gateway.restore_zone_a()
            s.remediation.failover = None
            if s.remediation.slack and ("콜드체인" in s.remediation.slack.manual_title or "COLDCHAIN" in s.remediation.slack.cause):
                s.remediation.slack = None
            s.remove_events("NODE_DOWN", "TEMP_HIGH", "ACTION_FAILOVER")
        elif sid == 6:  # 컨베이어 비정상 급가속 및 라인 진동
            s.active_scenarios.add(6)
            s.push_event("CONVEYOR_ANOMALY")
            ev = AlertEvent(type="CONVEYOR_ANOMALY", source="CONVEYOR_01", value=2.8, threshold=1.5)
            await self.engine.dispatch_now(ev)
            self.hub.emit_alert(ev)
        elif sid == 7:  # 컨베이어 라인 안정화 (인버터 PID 보정 ➔ 정속 1.0 m/s 복구)
            s.active_scenarios.discard(6)
            s.remove_events("CONVEYOR_ANOMALY")
            if s.remediation.slack and ("컨베이어" in s.remediation.slack.manual_title or "CONVEYOR" in s.remediation.slack.cause):
                s.remediation.slack = None
        return sorted(s.active_scenarios)

    async def step_motor_svm(self, delta: float = 1.5) -> float:
        """게이지 화살표 클릭 시 진동치를 delta(1.5)만큼 증감. 7.0 돌파 시 경보 & 인터록 자동 발동."""
        s = self.store
        val = self.edge.step_motor_svm(delta)
        s.motor.svm = val
        if val >= settings.svm_threshold and 1 not in s.active_scenarios:
            s.active_scenarios.add(1)
            s.motor.status = "WARNING"
            s.push_event("VIBRATION_HIGH")
            ev = AlertEvent(type="VIBRATION_HIGH", source="MOTOR_LINE_A_01", value=val, threshold=settings.svm_threshold)
            await self.engine.dispatch_now(ev)
            self.hub.emit_alert(ev)
        return val
