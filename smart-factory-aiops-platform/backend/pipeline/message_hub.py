"""Stage 3 — Message Hub: Pub/Sub 큐 (Queue-Based Load Leveling) & Fan-out (Route A / Route B)."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Optional, Protocol

from config import TOPIC_ALERT, TOPIC_RAW, settings
from models.schemas import AlertEvent
from state import StateStore

log = logging.getLogger("aiops.hub")


# ── 브로커 추상화 ────────────────────────────────────────────
class Broker(Protocol):
    def publish(self, topic: str, message: dict) -> None: ...
    async def pull(self, topic: str, max_messages: int = 1, timeout: float = 0.0) -> list[dict]: ...
    def backlog(self, topic: str) -> int: ...
    def purge(self, topic: str) -> None: ...


class InMemoryBroker:
    """로컬 시연용 — asyncio.Queue 기반 Pub/Sub 시뮬레이터."""

    def __init__(self) -> None:
        self._q: dict[str, asyncio.Queue] = {
            TOPIC_RAW: asyncio.Queue(),
            TOPIC_ALERT: asyncio.Queue(maxsize=1000),
        }
        self.dropped = 0

    def publish(self, topic: str, message: dict) -> None:
        try:
            self._q[topic].put_nowait(message)
        except asyncio.QueueFull:
            self.dropped += 1

    async def pull(self, topic: str, max_messages: int = 1, timeout: float = 0.0) -> list[dict]:
        q = self._q[topic]
        out: list[dict] = []
        if timeout > 0 and q.empty():
            try:
                out.append(await asyncio.wait_for(q.get(), timeout))
            except asyncio.TimeoutError:
                return out
        while len(out) < max_messages and not q.empty():
            out.append(q.get_nowait())
        return out

    def backlog(self, topic: str) -> int:
        return self._q[topic].qsize()

    def purge(self, topic: str) -> None:
        q = self._q[topic]
        while not q.empty():
            q.get_nowait()


class GcpPubSubBroker:
    """실제 GCP 연동 (AIOPS_MODE=gcp). google-cloud-pubsub 필요.

    backlog 는 로컬 카운터 기반 추정치이며, 운영에서는 Cloud Monitoring 지표
    `pubsub.googleapis.com/subscription/num_undelivered_messages` 로 대체하세요.
    """

    def __init__(self) -> None:
        from google.cloud import pubsub_v1  # lazy import

        self._pub = pubsub_v1.PublisherClient()
        self._sub = pubsub_v1.SubscriberClient()
        p = settings.gcp_project
        self._topic_path = {
            TOPIC_RAW: self._pub.topic_path(p, settings.pubsub_raw_topic),
            TOPIC_ALERT: self._pub.topic_path(p, settings.pubsub_alert_topic),
        }
        self._sub_path = {
            TOPIC_RAW: self._sub.subscription_path(p, settings.pubsub_raw_sub),
            TOPIC_ALERT: self._sub.subscription_path(p, settings.pubsub_alert_sub),
        }
        self._published = {TOPIC_RAW: 0, TOPIC_ALERT: 0}
        self._acked = {TOPIC_RAW: 0, TOPIC_ALERT: 0}

    def publish(self, topic: str, message: dict) -> None:
        self._pub.publish(self._topic_path[topic], json.dumps(message).encode())
        self._published[topic] += 1

    async def pull(self, topic: str, max_messages: int = 1, timeout: float = 0.0) -> list[dict]:
        def _pull():
            resp = self._sub.pull(
                request={"subscription": self._sub_path[topic], "max_messages": max_messages},
                timeout=max(timeout, 1.0),
            )
            if resp.received_messages:
                self._sub.acknowledge(
                    request={
                        "subscription": self._sub_path[topic],
                        "ack_ids": [m.ack_id for m in resp.received_messages],
                    }
                )
            return [json.loads(m.message.data) for m in resp.received_messages]

        try:
            msgs = await asyncio.to_thread(_pull)
        except Exception:
            return []
        self._acked[topic] += len(msgs)
        return msgs

    def backlog(self, topic: str) -> int:
        return max(0, self._published[topic] - self._acked[topic])

    def purge(self, topic: str) -> None:
        self._acked[topic] = self._published[topic]


def make_broker() -> Broker:
    if settings.use_gcp:
        try:
            return GcpPubSubBroker()
        except Exception:
            log.exception("GCP Pub/Sub 초기화 실패 → 인메모리 브로커로 대체")
    return InMemoryBroker()


# ── Message Hub ─────────────────────────────────────────────
class MessageHub:
    def __init__(self, store: StateStore, broker: Broker) -> None:
        self.store = store
        self.broker = broker
        self._throttle: dict[tuple[str, str], float] = {}
        self._backlog_latched = False

    # Route A: 모든 원시 로그 → Stage 4
    # Route B: 이상 징후 필터링 → Stage 5
    def publish(self, msg: dict) -> None:
        self.broker.publish(TOPIC_RAW, msg)
        self.store.meters.route_a.add(1)
        event = self._classify(msg)
        if event is not None:
            self.emit_alert(event)

    def emit_alert(self, event: AlertEvent) -> None:
        self.broker.publish(TOPIC_ALERT, event.model_dump())
        self.store.meters.route_b.add(1)
        self.store.push_event(event.type)

    def _classify(self, msg: dict) -> Optional[AlertEvent]:
        domain = msg.get("domain")
        metrics = msg.get("metrics", {})
        if domain == "FACTORY":
            svm = metrics.get("vibration_svm", 0.0)
            if svm >= settings.svm_threshold and self._allow("VIBRATION_HIGH", msg["sensor_id"]):
                return AlertEvent(type="VIBRATION_HIGH", source=msg["sensor_id"], value=svm,
                                  threshold=settings.svm_threshold)
        elif domain == "FULFILLMENT":
            temp = metrics.get("temperature_c", 0.0)
            zone = msg.get("node_zone")
            if temp >= settings.temp_threshold_c and self._allow("TEMP_HIGH", zone or ""):
                return AlertEvent(type="TEMP_HIGH", source=msg["sensor_id"], zone=zone, value=temp,
                                  threshold=settings.temp_threshold_c)
        return None

    def _allow(self, kind: str, key: str, interval_s: float = 1.0) -> bool:
        now = time.monotonic()
        if now - self._throttle.get((kind, key), 0.0) < interval_s:
            return False
        self._throttle[(kind, key)] = now
        return True

    @property
    def backlog(self) -> int:
        return self.broker.backlog(TOPIC_RAW)

    async def monitor(self) -> None:
        """적체량/병목 지수 실시간 계산 + BACKLOG_HIGH 이벤트 발행."""
        thr = settings.backlog_threshold
        while True:
            backlog = self.backlog
            q = self.store.queue
            q.backlog_count = backlog
            q.bottleneck_pct = round(backlog / thr * 100, 1)
            q.severity = "CRIT" if backlog >= thr else "WARN" if backlog >= thr * 0.7 else "OK"

            if backlog >= thr and not self._backlog_latched:
                self._backlog_latched = True
                self.emit_alert(AlertEvent(type="BACKLOG_HIGH", source="PUBSUB_RAW", value=backlog,
                                           threshold=thr))
            elif backlog < thr * 0.5:
                self._backlog_latched = False
            await asyncio.sleep(0.1)

    def reset(self) -> None:
        self.broker.purge(TOPIC_RAW)
        self.broker.purge(TOPIC_ALERT)
        self._backlog_latched = False
        self._throttle.clear()
