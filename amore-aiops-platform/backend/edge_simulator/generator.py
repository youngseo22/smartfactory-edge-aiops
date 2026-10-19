"""Stage 1 — Edge Layer: 공장 모터 & 물류 온·습도 센서 시뮬레이터 + 장애 주입기."""
from __future__ import annotations

import asyncio
import json
import logging
import random
from typing import Protocol

from config import settings
from models.schemas import utc_now_iso

log = logging.getLogger("aiops.edge")


# ── 전송 계층 추상화 ─────────────────────────────────────────
class Transport(Protocol):
    async def send(self, payload: dict) -> None: ...


class InProcessTransport:
    """로컬 시연: Gateway.ingest 를 직접 호출 (네트워크 없음)."""

    def __init__(self, gateway) -> None:
        self.gateway = gateway

    async def send(self, payload: dict) -> None:
        await self.gateway.ingest(payload)


class WebSocketTransport:
    """실제 구성: Gateway 의 /ws/ingest 로 JSON 전송 (끊기면 자동 재연결)."""

    def __init__(self, url: str) -> None:
        self.url = url
        self._ws = None

    async def _connect(self) -> None:
        import websockets  # uvicorn[standard] 에 포함

        self._ws = await websockets.connect(self.url, max_size=None)

    async def send(self, payload: dict) -> None:
        for _ in range(2):
            try:
                if self._ws is None:
                    await self._connect()
                await self._ws.send(json.dumps(payload))
                return
            except Exception:
                self._ws = None
                await asyncio.sleep(0.3)

    async def close(self) -> None:
        if self._ws is not None:
            await self._ws.close()


class EdgeSimulator:
    def __init__(self, transport: Transport) -> None:
        self.transport = transport
        self._rng = random.Random()
        self._seq = 0
        # 장애 주입 플래그
        self.motor_fault = False
        self.zone_a_heating = False
        self.zone_a_cut = False
        self._heat_ticks = 0
        # 내부 상태
        self._svm = settings.svm_normal
        self._target_svm = settings.svm_normal
        self._temp_a = 4.5
        self._temp_b = 4.2
        self._tasks: list[asyncio.Task] = []

    # ── 시나리오 제어 ───────────────────────────────────────
    def step_motor_svm(self, delta: float = 1.5) -> float:
        """SVM 진동 수치를 delta(기본 1.5)만큼 단계적으로 증가/감소. 8.5로 치솟지 않고 설정치 유지."""
        self._svm = round(min(10.0, max(0.5, self._svm + delta)), 2)
        self._target_svm = self._svm
        if self._svm >= settings.svm_threshold:
            self.motor_fault = True
        else:
            self.motor_fault = False
        return self._svm

    def trigger_motor_fault(self) -> None:
        self.motor_fault = True
        self._svm = settings.svm_fault
        self._target_svm = settings.svm_fault

    def trigger_zone_a_fault(self) -> None:
        self.zone_a_heating = True
        self._heat_ticks = 0
        self._temp_a = 9.2  # 시연용 즉각 반응 (임계치 8.0°C 즉각 돌파)

    def reset(self) -> None:
        self.motor_fault = False
        self.zone_a_heating = False
        self.zone_a_cut = False
        self._heat_ticks = 0
        self._temp_a = 4.5
        self._svm = settings.svm_normal
        self._target_svm = settings.svm_normal

    def reset_motor(self) -> None:
        """모터 정비/교체 완료: 모터 결함 단독 해제 및 진동치 즉시 정상화."""
        self.motor_fault = False
        self._svm = settings.svm_normal
        self._target_svm = settings.svm_normal

    def reset_zone_a(self) -> None:
        """Zone A 냉각기 수리 및 네트워크 복구 완료: 온도 4.5°C 복구 및 통신 재개."""
        self.zone_a_heating = False
        self.zone_a_cut = False
        self._heat_ticks = 0
        self._temp_a = 4.5

    async def order_burst(self) -> None:
        """마감 세일 주문 폭주: burst_total 건을 짧은 시간에 Gateway 로 주입."""
        per = settings.burst_total // settings.burst_chunks
        for _ in range(settings.burst_chunks):
            for _ in range(per):
                await self.transport.send(
                    {
                        "sensor_id": "ORDER_GW",
                        "domain": "ORDER",
                        "timestamp": utc_now_iso(),
                        "metrics": {"order_qty": 1.0},
                    }
                )
            await asyncio.sleep(0.025)

    # ── 센서 루프 ───────────────────────────────────────────
    def _motor_payload(self) -> dict:
        delta = self._target_svm - self._svm
        if abs(delta) > 0.05:
            step = max(-0.5, min(0.5, delta))
            self._svm += step
        noise = self._rng.uniform(-0.04, 0.04)
        current_svm = round(max(0.5, self._svm + noise), 2)
        return {
            "sensor_id": "MOTOR_LINE_A_01",
            "domain": "FACTORY",
            "timestamp": utc_now_iso(),
            "metrics": {
                "vibration_svm": current_svm,
                "torque_nm": round(3.2 + (current_svm - 2.8) * 0.18, 2),
                "rpm": round(1200 + self._rng.uniform(-8, 8) * (4 if self.motor_fault else 1)),
            },
            "status": "WARNING" if current_svm >= settings.svm_threshold else "NORMAL",
        }

    def _cold_payloads(self) -> list[dict]:
        self._seq += 1
        out: list[dict] = []
        # Zone A (Primary)
        if not self.zone_a_cut:
            if self.zone_a_heating:
                self._temp_a += 1.0
                self._heat_ticks += 1
            else:
                self._temp_a += (4.5 - self._temp_a) * 0.5 + self._rng.uniform(-0.15, 0.15)
            out.append(self._cold("COLD_ZONE_A_01", "ZONE_A", self._temp_a))
            if self.zone_a_heating and self._heat_ticks >= settings.heat_ticks_before_cut:
                self.zone_a_cut = True  # 이번 틱 이후 네트워크 단절
        # Zone B (Hot Standby — 항상 미러링 수집)
        self._temp_b += (4.2 - self._temp_b) * 0.4 + self._rng.uniform(-0.15, 0.15)
        out.append(self._cold("COLD_ZONE_B_01", "ZONE_B", self._temp_b))
        return out

    def _cold(self, sensor_id: str, zone: str, temp: float) -> dict:
        return {
            "sensor_id": sensor_id,
            "node_zone": zone,
            "domain": "FULFILLMENT",
            "timestamp": utc_now_iso(),
            "metrics": {
                "temperature_c": round(temp, 2),
                "humidity_pct": round(45 + self._rng.uniform(-1.0, 1.0), 1),
            },
            "heartbeat": True,
            "seq": self._seq,
        }

    async def _motor_loop(self) -> None:
        while True:
            try:
                await self.transport.send(self._motor_payload())
            except Exception:
                log.exception("motor send failed")
            await asyncio.sleep(settings.motor_period_s)

    async def _cold_loop(self) -> None:
        while True:
            try:
                for p in self._cold_payloads():
                    await self.transport.send(p)
            except Exception:
                log.exception("cold send failed")
            await asyncio.sleep(settings.cold_period_s)

    async def run(self) -> None:
        await asyncio.gather(self._motor_loop(), self._cold_loop())

