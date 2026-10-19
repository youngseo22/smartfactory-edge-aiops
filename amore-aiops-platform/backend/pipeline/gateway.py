"""Stage 2 — Ingestion Gateway: 수신 / Heartbeat Monitor / Dynamic Routing Table."""
from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass
from typing import Optional

from pydantic import ValidationError

from config import settings
from models.schemas import AlertEvent, SensorReading, SvmPoint, TempPoint, epoch_ms
from pipeline.message_hub import MessageHub
from state import StateStore

log = logging.getLogger("aiops.gateway")


@dataclass
class FailoverResult:
    from_zone: str
    to_zone: str
    replayed: int
    data_loss_pct: float


class IngestionGateway:
    def __init__(self, store: StateStore, hub: MessageHub) -> None:
        self.store = store
        self.hub = hub
        self._standby: deque[dict] = deque(maxlen=60)  # 대기(Backup) Zone 미러 수집 버퍼
        self._last_active_seq = 0
        self._down: set[str] = set()
        self.dropped = 0

    # ── 수신 ────────────────────────────────────────────────
    async def ingest(self, payload: dict | SensorReading) -> bool:
        try:
            r = payload if isinstance(payload, SensorReading) else SensorReading.model_validate(payload)
        except ValidationError:
            self.dropped += 1
            return False

        self.store.meters.edge.add(1)
        if r.domain == "ORDER":
            self.hub.publish(r.model_dump())
        elif r.domain == "FACTORY":
            self._on_motor(r)
        else:
            self._on_cold(r)
        return True

    def _on_motor(self, r: SensorReading) -> None:
        m = self.store.motor
        self.store.last_seen[r.sensor_id] = time.monotonic()
        m.sensor_id = r.sensor_id
        m.svm = r.metrics["vibration_svm"]
        m.torque_nm = r.metrics["torque_nm"]
        m.rpm = r.metrics["rpm"]
        m.status = "WARNING" if m.svm >= settings.svm_threshold else "NORMAL"
        self._down.discard(r.sensor_id)
        self.store.svm_history.append(SvmPoint(ts=int(r.event_epoch * 1000), svm=m.svm))
        self.hub.publish(r.model_dump())

    def _on_cold(self, r: SensorReading) -> None:
        zone = r.node_zone or "ZONE_A"
        zs = self.store.zones.get(zone)
        if zs is None:
            self.dropped += 1
            return
        self.store.last_seen[zone] = time.monotonic()
        self._down.discard(zone)
        zs.temp_c = r.metrics["temperature_c"]
        zs.humidity_pct = r.metrics["humidity_pct"]
        zs.status = "WARNING" if zs.temp_c >= settings.temp_threshold_c else "ONLINE"

        if zone == self.store.routing.active_zone:
            self._accept_cold(r)
        else:
            self._standby.append(r.model_dump())  # 핫 스탠바이: 수집만 하고 보관

    def _accept_cold(self, r: SensorReading) -> None:
        zone = r.node_zone or "ZONE_A"
        temp = r.metrics["temperature_c"]
        self.store.temp_history.append(
            TempPoint(
                ts=int(r.event_epoch * 1000),
                temp_a=temp if zone == "ZONE_A" else None,
                temp_b=temp if zone == "ZONE_B" else None,
                zone=zone,
            )
        )
        if r.seq:
            self._last_active_seq = max(self._last_active_seq, r.seq)
        self.hub.publish(r.model_dump())

    # ── Heartbeat Monitor ──────────────────────────────────
    async def heartbeat_monitor(self) -> None:
        while True:
            await asyncio.sleep(0.25)
            now = time.monotonic()
            for zone, zs in self.store.zones.items():
                seen = self.store.last_seen.get(zone)
                if seen is None or zone in self._down:
                    continue
                if now - seen > settings.heartbeat_timeout_s:
                    self._down.add(zone)
                    zs.status = "OFFLINE"
                    log.warning("NODE_DOWN %s (%.1fs 무수신)", zone, now - seen)
                    self.hub.emit_alert(
                        AlertEvent(type="NODE_DOWN", source=f"COLD_{zone}", zone=zone,
                                   value=round(now - seen, 1), threshold=settings.heartbeat_timeout_s)
                    )
            motor_seen = self.store.last_seen.get(self.store.motor.sensor_id)
            mid = self.store.motor.sensor_id
            if motor_seen is not None and mid not in self._down and now - motor_seen > settings.heartbeat_timeout_s:
                self._down.add(mid)
                self.store.motor.status = "OFFLINE"
                self.hub.emit_alert(AlertEvent(type="NODE_DOWN", source=mid, value=round(now - motor_seen, 1),
                                               threshold=settings.heartbeat_timeout_s))

    # ── Dynamic Routing: Failover ──────────────────────────
    def failover(self, from_zone: str, to_zone: str) -> Optional[FailoverResult]:
        store = self.store
        if store.zones[to_zone].status == "OFFLINE" or store.last_seen.get(to_zone) is None:
            return None
        rt = store.routing
        last_seq = self._last_active_seq

        # 그래프가 끊기지 않도록 마지막 A 포인트에 B 시리즈 시작점을 이어 붙임
        last = store.temp_history.last()
        if last is not None and last.temp_a is not None and last.temp_b is None:
            last.temp_b = last.temp_a

        rt.active_zone = to_zone
        rt.failover_active = True
        rt.table[from_zone] = to_zone
        rt.switched_at = epoch_ms()

        # 단절 구간(마지막 정상 수신 이후)의 Backup 미러 데이터를 재생(Replay) → 유실 0%
        missing = sorted((m for m in self._standby if (m.get("seq") or 0) > last_seq),
                         key=lambda m: m.get("seq") or 0)
        for m in missing:
            self._accept_cold(SensorReading.model_validate(m))
        self._standby.clear()

        expected = max(0, self._last_active_seq - last_seq)
        lost = max(0, expected - len(missing))
        rt.replayed = len(missing)
        rt.data_loss_pct = round(lost / expected * 100, 1) if expected else 0.0
        log.info("FAILOVER %s → %s (replay=%d, loss=%.1f%%)", from_zone, to_zone, len(missing), rt.data_loss_pct)
        return FailoverResult(from_zone, to_zone, len(missing), rt.data_loss_pct)

    def reset(self) -> None:
        now = time.monotonic()
        rt = self.store.routing
        rt.active_zone = rt.primary_zone
        rt.failover_active = False
        rt.data_loss_pct = 0.0
        rt.replayed = 0
        rt.switched_at = None
        rt.table = {"ZONE_A": "ZONE_A", "ZONE_B": "ZONE_B"}
        self._standby.clear()
        self._down.clear()
        for zone, zs in self.store.zones.items():
            self.store.last_seen[zone] = now  # 복구 직후 오탐(NODE_DOWN) 방지
            if zs.status == "OFFLINE":
                zs.status = "ONLINE"
        self.store.last_seen[self.store.motor.sensor_id] = now
