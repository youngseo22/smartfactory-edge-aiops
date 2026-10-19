"""[Stage 2] Ingestion Gateway — 고속 수신 · Heartbeat Monitor · Dynamic Routing Table.

- `/ws/ingest` 로 들어온 Edge 메시지를 검증(Pydantic)한 뒤 Message Hub 로 발행.
- Heartbeat Monitor: 콜드체인 구역별 Primary 업링크 마지막 수신 시각을 추적하여
  3초 이상 미수신 시 즉시 NODE_DOWN 이벤트를 Stage 5 로 직통 전달.
- Dynamic Routing Table: ZONE_A 장애 시 잔여 트래픽을 ZONE_B 백업 수집 서버로 우회.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

from pydantic import ValidationError

from config import settings
from models.schemas import ColdChainPayload, EventType, SensorStatus, ingest_adapter
from models.timeseries import RateMeter
from pipeline.message_hub import MessageHub

log = logging.getLogger("gateway")

ZONES = ("ZONE_A", "ZONE_B")
PRIMARY_ROUTES = {"ZONE_A": "ZONE_A", "ZONE_B": "ZONE_B"}


class IngestionGateway:
    def __init__(self, hub: MessageHub) -> None:
        self.hub = hub
        self.meter = RateMeter(2.0)
        self.routing_table: dict[str, str] = dict(PRIMARY_ROUTES)
        now = time.time()
        # 구역별 Primary 업링크 마지막 수신 시각 (Heartbeat)
        self.link_last_seen: dict[str, float] = {z: now for z in ZONES}
        # 구역 센서 자체의 마지막 수신 시각 (경로 무관)
        self.sensor_last_seen: dict[str, float] = {z: now for z in ZONES}
        self.node_down: dict[str, bool] = {z: False for z in ZONES}
        self.received_by_zone: dict[str, int] = {z: 0 for z in ZONES}
        self.replayed_msgs = 0
        self.rejected = 0
        self._hb_task: Optional[asyncio.Task] = None

    # ── lifecycle ─────────────────────────────────────────────
    async def start(self) -> None:
        self._hb_task = asyncio.create_task(self._heartbeat_monitor(), name="gateway-heartbeat")

    async def stop(self) -> None:
        if self._hb_task:
            self._hb_task.cancel()

    # ── routing ───────────────────────────────────────────────
    def route_for(self, zone: str) -> str:
        return self.routing_table.get(zone, zone)

    def failover(self, zone: str, backup: str) -> None:
        self.routing_table[zone] = backup
        log.warning("ROUTING %s → %s", zone, backup)

    def restore_routing(self) -> None:
        self.routing_table = dict(PRIMARY_ROUTES)
        now = time.time()
        for z in ZONES:
            self.link_last_seen[z] = now
            self.node_down[z] = False

    @property
    def failover_active(self) -> bool:
        return any(self.routing_table[z] != PRIMARY_ROUTES[z] for z in ZONES)

    # ── ingestion ─────────────────────────────────────────────
    async def ingest_batch(self, messages: list[dict[str, Any]], uplink: str = "FACTORY") -> int:
        now = time.time()
        accepted = 0
        for raw in messages:
            try:
                msg = ingest_adapter.validate_python(raw)
            except ValidationError:
                self.rejected += 1
                continue
            if isinstance(msg, ColdChainPayload):
                zone = msg.node_zone
                msg.routed_via = uplink if uplink in ZONES else zone
                self.sensor_last_seen[zone] = now
                self.received_by_zone[zone] = self.received_by_zone.get(zone, 0) + 1
                if msg.replayed:
                    self.replayed_msgs += 1
                if msg.routed_via == zone:
                    # Primary 업링크 heartbeat
                    self.link_last_seen[zone] = now
                    if self.node_down.get(zone):
                        self.node_down[zone] = False
                        log.info("NODE_UP %s", zone)
            self.hub.publish(msg)
            accepted += 1
        self.meter.mark(accepted, now)
        return accepted

    # ── heartbeat monitor ─────────────────────────────────────
    async def _heartbeat_monitor(self) -> None:
        while True:
            await asyncio.sleep(0.2)
            now = time.time()
            for zone in ZONES:
                silent = now - self.link_last_seen[zone]
                if silent >= settings.heartbeat_timeout_s and not self.node_down[zone]:
                    self.node_down[zone] = True
                    log.error("NODE_DOWN %s (silent %.1fs)", zone, silent)
                    # Stage 5 직통 전달 (Route B)
                    self.hub.emit(
                        EventType.NODE_DOWN,
                        zone,
                        SensorStatus.CRITICAL,
                        {"silent_s": round(silent, 2), "backup": "ZONE_B" if zone == "ZONE_A" else "ZONE_A"},
                        throttle_s=0.0,
                    )

    def link_age(self, zone: str) -> float:
        return round(time.time() - self.link_last_seen[zone], 2)
