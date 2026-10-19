"""플랫폼 런타임 — 5단계 컴포넌트 와이어링 · 실시간 텔레메트리 · 대시보드 스냅샷 빌더."""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Optional

from aiops.rag_agent import RagAgent
from aiops.remediation import AIOpsEngine
from config import settings
from edge_simulator.generator import EdgeSimulator, InProcessTransport, WebSocketTransport
from models.schemas import (
    ColdChainPayload,
    ColdChainState,
    CosmeticMotorPayload,
    DashboardSnapshot,
    FactoryState,
    MotorState,
    PipelineStats,
    RoutingState,
    ScenarioId,
    SensorStatus,
    SvmPoint,
    TempPoint,
    ZoneState,
    ZoneStatus,
)
from models.timeseries import BucketedTimeSeries
from pipeline.dataflow_worker import DataflowWorkerPool
from pipeline.gateway import IngestionGateway
from pipeline.message_hub import MessageHub

log = logging.getLogger("runtime")


class Platform:
    def __init__(self) -> None:
        self.hub = MessageHub()
        self.gateway = IngestionGateway(self.hub)
        self.workers = DataflowWorkerPool(self.hub)
        self.rag = RagAgent()
        self.engine = AIOpsEngine(self.hub, self.gateway, self.workers, self.rag, loss_fn=self._loss)

        transport_kind = os.getenv("EDGE_TRANSPORT", "inproc").lower()
        if transport_kind == "ws":
            port = os.getenv("PORT", "8000")
            transport = WebSocketTransport(os.getenv("EDGE_WS_URL", f"ws://127.0.0.1:{port}/ws/ingest"))
        else:
            transport = InProcessTransport(self.gateway)
        self.transport_kind = transport_kind
        self.simulator = EdgeSimulator(transport)

        # 실시간 텔레메트리 (BigQuery 실시간 뷰 대체)
        self.temp_ts = BucketedTimeSeries(settings.history_bucket_s, settings.history_points)
        self.svm_ts = BucketedTimeSeries(settings.history_bucket_s, settings.history_points)
        self.latest_motor: Optional[CosmeticMotorPayload] = None
        self.latest_zone: dict[str, ColdChainPayload] = {}
        self.hub.add_tap(self._tap)

        self.scenario = ScenarioId.NORMAL

    # ── lifecycle ─────────────────────────────────────────────
    async def start(self) -> None:
        await self.hub.start()
        await self.gateway.start()
        await self.workers.start()
        await self.engine.start()
        await self.simulator.start()
        log.info("platform started (mode=%s, edge=%s)", "GCP" if settings.use_gcp else "MOCK", self.transport_kind)

    async def stop(self) -> None:
        await self.simulator.stop()
        await self.engine.stop()
        await self.workers.stop()
        await self.gateway.stop()
        await self.hub.stop()

    # ── scenario control ──────────────────────────────────────
    def set_scenario(self, scenario: ScenarioId) -> None:
        self.scenario = scenario
        self.engine.reset()
        self.gateway.restore_routing()
        self.hub.reset_throttle()
        if self.workers.target_workers != settings.base_workers or self.workers.active_workers != settings.base_workers:
            self.workers.scale_to(settings.base_workers)
        self.simulator.set_scenario(scenario)

    # ── telemetry tap ─────────────────────────────────────────
    def _tap(self, msg: Any) -> None:
        if isinstance(msg, CosmeticMotorPayload):
            self.latest_motor = msg
            m = msg.metrics
            self.svm_ts.update(msg.timestamp.timestamp(), svm=m.vibration_svm, torque=m.torque_nm, rpm=m.rpm)
        elif isinstance(msg, ColdChainPayload):
            ts = msg.timestamp.timestamp()
            temp = msg.metrics.temperature_c
            if msg.node_zone == "ZONE_A":
                self.temp_ts.update(ts, zone_a=temp, route=msg.routed_via)
            else:
                self.temp_ts.update(ts, zone_b=temp)
            if not msg.replayed:
                self.latest_zone[msg.node_zone] = msg

    def _loss(self) -> tuple[float, int]:
        generated = self.simulator.zone_a_generated
        received = self.gateway.received_by_zone.get("ZONE_A", 0)
        pending = self.simulator.pending_buffer
        lost = max(0, generated - received - pending)
        pct = round(lost / generated * 100, 2) if generated else 0.0
        return pct, self.gateway.replayed_msgs

    # ── snapshot ──────────────────────────────────────────────
    def _temp_history(self, now: float) -> list[TempPoint]:
        rows = self.temp_ts.window(("zone_a", "zone_b", "route"), now)
        points = [TempPoint(**r) for r in rows]
        for p in points:
            if p.zone_a is None:
                continue
            if p.route == "ZONE_B":
                p.a_backup = p.zone_a
            else:
                p.a_primary = p.zone_a
        # 경로 전환 지점 브릿지 → 선이 끊기지 않고 이어짐
        for i in range(1, len(points)):
            prev, cur = points[i - 1], points[i]
            if prev.zone_a is None or cur.zone_a is None:
                continue
            if prev.route != "ZONE_B" and cur.route == "ZONE_B":
                prev.a_backup = prev.zone_a
            elif prev.route == "ZONE_B" and cur.route != "ZONE_B":
                prev.a_primary = prev.zone_a
        return points

    def _zones(self, now: float) -> dict[str, ZoneState]:
        gw = self.gateway
        out: dict[str, ZoneState] = {}
        a = self.latest_zone.get("ZONE_A")
        a_age = gw.link_age("ZONE_A")
        rerouted = gw.route_for("ZONE_A") != "ZONE_A"
        if gw.node_down["ZONE_A"] or rerouted:
            a_status = ZoneStatus.OFFLINE
        elif a_age > 1.0 or (a and a.metrics.temperature_c > settings.temp_threshold_c):
            a_status = ZoneStatus.WARNING
        else:
            a_status = ZoneStatus.ONLINE
        out["ZONE_A"] = ZoneState(
            zone="ZONE_A",
            role="PRIMARY",
            status=a_status,
            temperature_c=a.metrics.temperature_c if a else None,
            humidity_pct=a.metrics.humidity_pct if a else None,
            last_seen_ago_s=a_age,
            link_up=not gw.node_down["ZONE_A"] and a_age < settings.heartbeat_timeout_s,
        )
        b = self.latest_zone.get("ZONE_B")
        out["ZONE_B"] = ZoneState(
            zone="ZONE_B",
            role="BACKUP",
            status=ZoneStatus.BACKUP_ON if rerouted else ZoneStatus.STANDBY,
            temperature_c=b.metrics.temperature_c if b else None,
            humidity_pct=b.metrics.humidity_pct if b else None,
            last_seen_ago_s=gw.link_age("ZONE_B"),
            link_up=not gw.node_down["ZONE_B"],
        )
        return out

    def snapshot(self) -> DashboardSnapshot:
        now = time.time()
        hub, gw, wk = self.hub, self.gateway, self.workers
        m = self.latest_motor
        svm = m.metrics.vibration_svm if m else 0.0
        motor = MotorState(
            sensor_id=m.sensor_id if m else "MOTOR_LINE_A_01",
            vibration_svm=svm,
            torque_nm=m.metrics.torque_nm if m else 0.0,
            rpm=m.metrics.rpm if m else 0,
            status=m.status if m else SensorStatus.NORMAL,
            threshold=settings.vibration_threshold,
            critical=settings.vibration_critical,
        )
        svm_history = [SvmPoint(**r) for r in self.svm_ts.window(("svm", "torque", "rpm"), now)]
        loss, recovered = self._loss()

        return DashboardSnapshot(
            ts=now,
            scenario=self.scenario,
            mode="GCP" if settings.use_gcp else "MOCK",
            pipeline=PipelineStats(
                edge_rate=self.simulator.meter.rate(now),
                ingress_rate=gw.meter.rate(now),
                route_a_rate=hub.route_a_meter.rate(now),
                route_b_rate=hub.route_b_meter.rate(now),
                consume_rate=wk.meter.rate(now),
                backlog_count=hub.backlog_count,
                backlog_threshold=settings.backlog_threshold,
                bottleneck_pct=hub.bottleneck_pct,
                bq_rows=wk.sink.rows_written,
                ai_events=self.engine.ai_events,
            ),
            factory=FactoryState(
                motor=motor,
                svm_history=svm_history,
                worker_pods=wk.views(),
                active_workers=wk.active_workers,
                base_workers=settings.base_workers,
                max_workers=settings.max_workers,
                throughput_pct=round(wk.active_workers / settings.base_workers * 100),
            ),
            coldchain=ColdChainState(
                temp_history=self._temp_history(now),
                zones=self._zones(now),
                temp_threshold=settings.temp_threshold_c,
            ),
            routing=RoutingState(
                table=dict(gw.routing_table),
                failover_active=gw.failover_active,
                data_loss_pct=loss,
                buffered_msgs=self.simulator.pending_buffer,
                recovered_msgs=recovered,
            ),
            remediation=self.engine.state(),
            actions=list(self.engine.actions),
        )
