"""[Stage 3] Message Hub — Pub/Sub Queue-Based Load Leveling & Fan-out.

- Route A (전체 로그)  : 모든 원시 메시지 → Stage 4 (Dataflow/BigQuery) 큐
- Route B (이상 징후)  : vibration_svm >= 7.0 · backlog_count >= 1000 · NODE_DOWN
                         · temperature > 8.0 → Stage 5 (AIOps Engine) 큐

로컬 시연 시 `asyncio.Queue` 가 Pub/Sub 토픽/구독을 대체한다.
`USE_GCP=true` 이면 PubSubMirror 가 동일 메시지를 실제 Pub/Sub 토픽에 미러링 발행한다.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Callable, Optional

from config import settings
from models.schemas import (
    ColdChainPayload,
    CosmeticMotorPayload,
    EventType,
    PipelineEvent,
    SensorStatus,
)
from models.timeseries import RateMeter

log = logging.getLogger("hub")

Message = Any  # CosmeticMotorPayload | ColdChainPayload | OrderEvent
Tap = Callable[[Message], None]


class PubSubMirror:
    """실제 GCP Pub/Sub 발행 어댑터 (USE_GCP=true 일 때만 활성화)."""

    def __init__(self) -> None:
        self.enabled = False
        self._publisher: Any = None
        if not settings.use_gcp:
            return
        try:
            from google.cloud import pubsub_v1  # type: ignore

            self._publisher = pubsub_v1.PublisherClient(
                batch_settings=pubsub_v1.types.BatchSettings(max_messages=500, max_latency=0.05)
            )
            self._topic_raw = self._publisher.topic_path(settings.gcp_project, settings.pubsub_topic_raw)
            self._topic_anomaly = self._publisher.topic_path(settings.gcp_project, settings.pubsub_topic_anomaly)
            self.enabled = True
            log.info("Pub/Sub mirror enabled (%s)", settings.gcp_project)
        except Exception as exc:  # noqa: BLE001
            log.warning("Pub/Sub mirror disabled: %s", exc)

    def publish(self, route: str, data: dict[str, Any]) -> None:
        if not self.enabled:
            return
        topic = self._topic_raw if route == "A" else self._topic_anomaly
        try:
            self._publisher.publish(topic, json.dumps(data, default=str).encode())
        except Exception as exc:  # noqa: BLE001
            log.debug("pubsub publish failed: %s", exc)


class MessageHub:
    def __init__(self) -> None:
        self.route_a: asyncio.Queue[Message] = asyncio.Queue()
        self.route_b: asyncio.Queue[PipelineEvent] = asyncio.Queue()
        self.route_a_meter = RateMeter(2.0)
        self.route_b_meter = RateMeter(5.0)
        self.mirror = PubSubMirror()
        self._taps: list[Tap] = []
        self._last_emit: dict[tuple[str, str], float] = {}
        self._monitor_task: Optional[asyncio.Task] = None
        self.peak_backlog = 0

    # ── wiring ────────────────────────────────────────────────
    def add_tap(self, tap: Tap) -> None:
        """실시간 뷰(대시보드 시계열) 용 관찰자 등록."""
        self._taps.append(tap)

    async def start(self) -> None:
        self._monitor_task = asyncio.create_task(self._backlog_monitor(), name="hub-backlog-monitor")

    async def stop(self) -> None:
        if self._monitor_task:
            self._monitor_task.cancel()

    # ── metrics ───────────────────────────────────────────────
    @property
    def backlog_count(self) -> int:
        return self.route_a.qsize()

    @property
    def bottleneck_pct(self) -> float:
        return round(self.backlog_count / settings.backlog_threshold * 100, 1)

    # ── publish (Fan-out) ─────────────────────────────────────
    def publish(self, msg: Message) -> None:
        now = time.time()
        # Route A : 전체 로그
        self.route_a.put_nowait(msg)
        self.route_a_meter.mark(1, now)
        if self.mirror.enabled:
            self.mirror.publish("A", msg.model_dump(mode="json"))

        for tap in self._taps:
            try:
                tap(msg)
            except Exception:  # noqa: BLE001
                log.exception("tap failed")

        # Route B : 이상 징후 필터
        if isinstance(msg, CosmeticMotorPayload):
            svm = msg.metrics.vibration_svm
            if svm >= settings.vibration_threshold:
                sev = SensorStatus.CRITICAL if svm >= settings.vibration_critical else SensorStatus.WARNING
                self.emit(
                    EventType.VIBRATION_ANOMALY,
                    msg.sensor_id,
                    sev,
                    {"vibration_svm": svm, "torque_nm": msg.metrics.torque_nm, "rpm": msg.metrics.rpm},
                )
        elif isinstance(msg, ColdChainPayload):
            temp = msg.metrics.temperature_c
            if temp > settings.temp_threshold_c and not msg.replayed:
                self.emit(EventType.TEMP_HIGH, msg.node_zone, SensorStatus.WARNING, {"temperature_c": temp})

    def emit(
        self,
        event_type: EventType,
        source: str,
        severity: SensorStatus = SensorStatus.WARNING,
        payload: Optional[dict[str, Any]] = None,
        *,
        throttle_s: float = 2.0,
    ) -> bool:
        """Route B 로 이상 이벤트 발행 (동일 이벤트 throttle)."""
        now = time.time()
        key = (event_type.value, source)
        if now - self._last_emit.get(key, 0.0) < throttle_s:
            return False
        self._last_emit[key] = now
        event = PipelineEvent(event_type=event_type, source=source, severity=severity, ts=now, payload=payload or {})
        self.route_b.put_nowait(event)
        self.route_b_meter.mark(1, now)
        if self.mirror.enabled:
            self.mirror.publish("B", event.model_dump(mode="json"))
        return True

    def reset_throttle(self) -> None:
        self._last_emit.clear()
        self.peak_backlog = 0

    async def _backlog_monitor(self) -> None:
        while True:
            await asyncio.sleep(0.25)
            backlog = self.backlog_count
            self.peak_backlog = max(self.peak_backlog, backlog)
            if backlog >= settings.backlog_threshold:
                self.emit(
                    EventType.BACKLOG_HIGH,
                    "PUBSUB_IOT_RAW",
                    SensorStatus.CRITICAL if backlog >= settings.backlog_threshold * 1.15 else SensorStatus.WARNING,
                    {"backlog_count": backlog, "bottleneck_pct": self.bottleneck_pct},
                    throttle_s=3.0,
                )
