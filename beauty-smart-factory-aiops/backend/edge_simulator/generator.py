"""[Stage 1] Edge Layer — IoT 센서 시뮬레이터 & 장애 주입기.

- COSMETIC_MOTOR  : 캡 조립 모터 (진동 SVM / 토크 / RPM)
- COLDCHAIN_ENV   : ZONE_A (Primary) · ZONE_B (Backup) 온·습도 센서
- ORDER           : 마감 세일 주문 이벤트 (큐 적체 유발)

전송 계층은 추상화되어 있다.
- InProcessTransport : 같은 프로세스의 Gateway 로 직접 전달 (기본값, 가장 안정적)
- WebSocketTransport : `/ws/ingest` 로 실제 WebSocket 전송 (EDGE_TRANSPORT=ws)

ZONE_A 엣지 노드는 Store-and-Forward 버퍼를 가진다. Primary 업링크가 끊기면
측정값을 로컬에 버퍼링하고, Gateway 라우팅 테이블이 ZONE_B 백업 수집 서버로
전환되면 버퍼를 원래 타임스탬프 그대로 재전송한다 → 데이터 유실 0%.
"""
from __future__ import annotations

import asyncio
import json
import logging
import math
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import deque
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

from config import settings
from models.schemas import ScenarioId
from models.timeseries import RateMeter

if TYPE_CHECKING:  # pragma: no cover
    from pipeline.gateway import IngestionGateway

log = logging.getLogger("edge")

SKUS = ["CUSHION-21N", "SERUM-50ML", "LIPTINT-03", "CREAM-GOLD", "TONER-200", "SUNCARE-SPF50"]


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


# ════════════════════════════════════════════════════════════════
# Transport abstraction
# ════════════════════════════════════════════════════════════════
class EdgeTransport(ABC):
    @abstractmethod
    async def send(self, messages: list[dict[str, Any]], uplink: str) -> bool: ...

    @abstractmethod
    def route_for(self, zone: str) -> str: ...

    async def start(self) -> None:  # pragma: no cover - optional
        return None

    async def stop(self) -> None:  # pragma: no cover - optional
        return None


class InProcessTransport(EdgeTransport):
    def __init__(self, gateway: "IngestionGateway") -> None:
        self.gateway = gateway

    async def send(self, messages: list[dict[str, Any]], uplink: str) -> bool:
        if messages:
            await self.gateway.ingest_batch(messages, uplink=uplink)
        return True

    def route_for(self, zone: str) -> str:
        return self.gateway.route_for(zone)


class WebSocketTransport(EdgeTransport):
    """실제 WebSocket 으로 `/ws/ingest` 에 전송. Gateway ack 로 라우팅 테이블 동기화."""

    def __init__(self, url: str) -> None:
        self.url = url
        self._ws: Any = None
        self._routing: dict[str, str] = {"ZONE_A": "ZONE_A", "ZONE_B": "ZONE_B"}
        self._reader: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    async def _connect(self) -> None:
        from websockets.asyncio.client import connect  # lazy import

        self._ws = await connect(self.url, max_size=None)
        self._reader = asyncio.create_task(self._read_acks())
        log.info("edge ws connected → %s", self.url)

    async def _read_acks(self) -> None:
        try:
            async for raw in self._ws:
                try:
                    ack = json.loads(raw)
                    if isinstance(ack.get("routing"), dict):
                        self._routing = ack["routing"]
                except ValueError:
                    continue
        except Exception:  # connection closed
            pass
        finally:
            self._ws = None

    async def send(self, messages: list[dict[str, Any]], uplink: str) -> bool:
        if not messages:
            return True
        async with self._lock:
            try:
                if self._ws is None:
                    await self._connect()
                await self._ws.send(json.dumps({"uplink": uplink, "messages": messages}))
                return True
            except Exception as exc:  # noqa: BLE001
                log.warning("edge ws send failed: %s", exc)
                self._ws = None
                return False

    def route_for(self, zone: str) -> str:
        return self._routing.get(zone, zone)

    async def stop(self) -> None:
        if self._ws is not None:
            await self._ws.close()
        if self._reader:
            self._reader.cancel()


# ════════════════════════════════════════════════════════════════
# Edge simulator
# ════════════════════════════════════════════════════════════════
class EdgeSimulator:
    def __init__(self, transport: EdgeTransport) -> None:
        self.transport = transport
        self.scenario: ScenarioId = ScenarioId.NORMAL
        self.scenario_started = time.time()
        self.meter = RateMeter(window_s=2.0)

        self._seq = {"MOTOR": 0, "ZONE_A": 0, "ZONE_B": 0, "ORDER": 0}
        self._order_carry = 0.0
        self._task: Optional[asyncio.Task] = None
        self._rng = random.Random(42)

        # 장애 주입 상태
        self.zone_a_link_up = True
        self.zone_a_buffer: deque[dict[str, Any]] = deque(maxlen=5000)
        self.zone_a_generated = 0

        # 현재 물리량 (스무딩)
        self._svm = 2.4
        self._torque = 3.6
        self._temp_a = 4.5
        self._temp_b = 4.2

    # ── lifecycle ──────────────────────────────────────────────
    async def start(self) -> None:
        await self.transport.start()
        self._task = asyncio.create_task(self._run(), name="edge-simulator")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
        await self.transport.stop()

    def set_scenario(self, scenario: ScenarioId) -> None:
        self.scenario = scenario
        self.scenario_started = time.time()
        self._order_carry = 0.0
        self.zone_a_link_up = True
        log.info("edge scenario → %s", scenario.value)

    @property
    def elapsed(self) -> float:
        return time.time() - self.scenario_started

    @property
    def pending_buffer(self) -> int:
        return len(self.zone_a_buffer)

    # ── main loop ─────────────────────────────────────────────
    async def _run(self) -> None:
        tick = settings.edge_tick_s
        next_at = time.perf_counter()
        while True:
            try:
                await self._tick(tick)
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001
                log.exception("edge tick failed")
            next_at += tick
            await asyncio.sleep(max(0.0, next_at - time.perf_counter()))

    async def _tick(self, dt: float) -> None:
        now = time.time()
        t = self.elapsed
        s1 = self.scenario == ScenarioId.SCENARIO_1
        s2 = self.scenario == ScenarioId.SCENARIO_2

        # ── Motor ──
        target_svm = 8.5 if (s1 and t >= 0.5) else 2.4
        target_torque = 4.2 if (s1 and t >= 0.5) else 3.6
        alpha = 0.45 if s1 else 0.25
        self._svm += (target_svm - self._svm) * alpha
        self._torque += (target_torque - self._torque) * alpha
        svm = max(0.1, self._svm + self._rng.gauss(0, 0.18 if s1 else 0.12))
        torque = max(0.5, self._torque + self._rng.gauss(0, 0.05))
        rpm = int(1200 + self._rng.gauss(0, 35 if s1 else 6) + (math.sin(now * 7) * 40 if s1 else 0))
        status = "CRITICAL" if svm >= settings.vibration_critical else "WARNING" if svm >= settings.vibration_threshold else "NORMAL"
        self._seq["MOTOR"] += 1
        motor = {
            "sensor_id": "MOTOR_LINE_A_01",
            "domain": "FACTORY",
            "timestamp": iso(now),
            "metrics": {"vibration_svm": round(svm, 2), "torque_nm": round(torque, 2), "rpm": rpm},
            "status": status,
            "seq": self._seq["MOTOR"],
        }

        # ── Cold-chain ──
        if s2:
            ramp = min(1.0, t / settings.s2_temp_ramp_s)
            target_a = 4.5 + ramp * 7.0  # → 11.5 ℃
            self.zone_a_link_up = t < settings.s2_link_fault_after_s
        else:
            target_a = 4.5
        self._temp_a += (target_a - self._temp_a) * 0.35
        self._temp_b += (4.2 - self._temp_b) * 0.2
        temp_a = self._temp_a + self._rng.gauss(0, 0.06)
        temp_b = self._temp_b + self._rng.gauss(0, 0.05)
        self._seq["ZONE_A"] += 1
        self._seq["ZONE_B"] += 1
        self.zone_a_generated += 1
        zone_a = {
            "sensor_id": "COLD_ZONE_A_01",
            "node_zone": "ZONE_A",
            "domain": "FULFILLMENT",
            "timestamp": iso(now),
            "metrics": {"temperature_c": round(temp_a, 2), "humidity_pct": round(45 + self._rng.gauss(0, 0.4) + (6 if s2 else 0), 1)},
            "heartbeat": True,
            "seq": self._seq["ZONE_A"],
        }
        zone_b = {
            "sensor_id": "COLD_ZONE_B_01",
            "node_zone": "ZONE_B",
            "domain": "FULFILLMENT",
            "timestamp": iso(now),
            "metrics": {"temperature_c": round(temp_b, 2), "humidity_pct": round(44 + self._rng.gauss(0, 0.4), 1)},
            "heartbeat": True,
            "seq": self._seq["ZONE_B"],
        }

        # ── Orders (traffic) ──
        rate = settings.base_order_rate
        if s1:
            if t < settings.surge_burst_s:
                rate = settings.surge_burst_orders / settings.surge_burst_s
            elif t < settings.surge_duration_s:
                rate = settings.surge_order_rate
        self._order_carry += rate * dt
        n_orders = int(self._order_carry)
        self._order_carry -= n_orders
        orders = []
        for _ in range(n_orders):
            self._seq["ORDER"] += 1
            orders.append({
                "order_id": uuid.uuid4().hex[:12],
                "domain": "ORDER",
                "timestamp": iso(now),
                "sku": self._rng.choice(SKUS),
                "qty": self._rng.randint(1, 3),
                "seq": self._seq["ORDER"],
            })

        # ── Delivery ──
        factory_batch = [motor, *orders]
        await self.transport.send(factory_batch, uplink="FACTORY")
        await self.transport.send([zone_b], uplink=self.transport.route_for("ZONE_B"))
        await self._deliver_zone_a(zone_a)
        self.meter.mark(len(factory_batch) + 2, now)

    async def _deliver_zone_a(self, reading: dict[str, Any]) -> None:
        uplink = self.transport.route_for("ZONE_A")
        primary_path = uplink == "ZONE_A"
        if primary_path and not self.zone_a_link_up:
            # 네트워크 단절 → Store-and-Forward 버퍼링
            self.zone_a_buffer.append(reading)
            return
        batch: list[dict[str, Any]] = []
        while self.zone_a_buffer:
            buffered = self.zone_a_buffer.popleft()
            buffered["replayed"] = True
            batch.append(buffered)
        batch.append(reading)
        ok = await self.transport.send(batch, uplink=uplink)
        if not ok:
            for item in reversed(batch):
                self.zone_a_buffer.appendleft(item)
