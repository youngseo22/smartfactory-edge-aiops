"""Stage 5 — AIOps Engine: Route B 이상 징후 소비 → 3대 자율 대응(Slack / Scale-up / Failover) 실행."""
from __future__ import annotations

import asyncio
import json
import logging
import time
import urllib.request
from typing import Coroutine, Optional

from aiops.rag_agent import RagAgent
from config import TOPIC_ALERT, settings
from models.schemas import AlertEvent, FailoverAction, ScaleAction, SlackCard, epoch_ms
from pipeline.dataflow_worker import DataflowWorkerPool
from pipeline.gateway import IngestionGateway
from pipeline.message_hub import Broker
from state import StateStore

log = logging.getLogger("aiops.remediation")

SLACK_COOLDOWN_S = 60.0


class SlackNotifier:
    """Mock: 메모리에 보관. SLACK_WEBHOOK_URL 이 있으면 실제 Slack 으로도 전송."""

    def __init__(self) -> None:
        self.sent: list[SlackCard] = []

    async def send(self, card: SlackCard) -> None:
        self.sent.append(card)
        if not settings.slack_webhook_url:
            return
        body = json.dumps({
            "text": f":rotating_light: {card.cause} — Manual p.{card.manual_page}: {card.key_action}",
        }).encode()
        req = urllib.request.Request(settings.slack_webhook_url, body, {"Content-Type": "application/json"})
        try:
            await asyncio.to_thread(urllib.request.urlopen, req, None, 5)
        except Exception:
            log.exception("Slack webhook 전송 실패")


class Remediator:
    """3대 자율 대응 실행기."""

    def __init__(self, store: StateStore, rag: RagAgent, notifier: SlackNotifier,
                 pool: DataflowWorkerPool, gateway: IngestionGateway) -> None:
        self.store, self.rag, self.notifier, self.pool, self.gateway = store, rag, notifier, pool, gateway

    # [Action A] SLACK_ALERT — RAG 로 매뉴얼 검색 후 토크 조절 가이드 알림
    async def slack_alert(self, event: AlertEvent) -> None:
        m = self.store.motor
        diag = await self.rag.diagnose(event, {"svm": m.svm, "torque_nm": m.torque_nm, "rpm": m.rpm})
        card = SlackCard(
            severity="CRIT",  # VIBRATION_HIGH 는 임계치(7.0) 초과 = 위험 수준
            manual_page=diag.manual_page, manual_title=diag.manual_title,
            key_action=diag.key_action, cause=diag.cause, confidence=diag.confidence,
            svm=round(event.value or m.svm, 1), ts=epoch_ms(),
        )
        self.store.remediation.slack = card
        self.store.push_event("ACTION_SLACK")
        await self.notifier.send(card)

    # [Action B] CONTAINER_SCALE_UP — 워커 2 → 6
    async def scale_up(self, event: AlertEvent) -> None:
        before = self.store.active_pod_count()
        if before >= settings.max_workers:
            return
        act = ScaleAction(from_pods=before, to_pods=settings.max_workers, status="RUNNING", ts=epoch_ms())
        self.store.remediation.scale = act
        self.store.push_event("ACTION_SCALE")
        await self.pool.scale_to(settings.max_workers)
        if self.store.remediation.scale is act:
            act.status = "DONE"

    # [Action C] NODE_FAILOVER — ZONE_A → ZONE_B
    async def node_failover(self, event: AlertEvent) -> None:
        rt = self.store.routing
        src = event.zone or rt.active_zone
        dst = rt.backup_zone if src == rt.primary_zone else rt.primary_zone
        res = self.gateway.failover(src, dst)
        self.store.push_event("ACTION_FAILOVER")
        self.store.remediation.failover = FailoverAction(
            from_zone=src, to_zone=dst, ts=epoch_ms(),
            status="DONE" if res else "NO_BACKUP",
            data_loss_pct=res.data_loss_pct if res else 100.0,
            replayed=res.replayed if res else 0,
        )


class AIOpsEngine:
    def __init__(self, store: StateStore, broker: Broker, remediator: Remediator, pool: DataflowWorkerPool) -> None:
        self.store, self.broker, self.rem, self.pool = store, broker, remediator, pool
        self._tasks: set[asyncio.Task] = set()
        self._last_slack = float("-inf")

    def _spawn(self, coro: Coroutine) -> None:
        t = asyncio.create_task(coro)
        self._tasks.add(t)
        t.add_done_callback(self._on_done)

    def _on_done(self, t: asyncio.Task) -> None:
        self._tasks.discard(t)
        if not t.cancelled() and t.exception():
            log.error("remediation action failed", exc_info=t.exception())

    def _dispatch(self, ev: AlertEvent) -> None:
        rem = self.store.remediation
        now = time.monotonic()
        if ev.type == "VIBRATION_HIGH":
            if now - self._last_slack > SLACK_COOLDOWN_S:
                self._last_slack = now
                self._spawn(self.rem.slack_alert(ev))
        elif ev.type == "BACKLOG_HIGH":
            if not (rem.scale and rem.scale.status == "RUNNING"):
                self._spawn(self.rem.scale_up(ev))
        elif ev.type == "NODE_DOWN":
            # 서빙 중인 구역이 끊겼을 때만 Failover
            if ev.zone and ev.zone == self.store.routing.active_zone:
                self._spawn(self.rem.node_failover(ev))
        # TEMP_HIGH 는 Gateway 가 Zone 상태(WARNING)로 이미 표시 — 별도 액션 없음

    async def run(self) -> None:
        while True:
            for raw in await self.broker.pull(TOPIC_ALERT, 20, timeout=0.5):
                try:
                    self._dispatch(AlertEvent.model_validate(raw))
                except Exception:
                    log.exception("alert dispatch failed")

    async def autoscale_down_loop(self) -> None:
        """적체 해소 후 일정 시간이 지나면 워커를 기본 수로 되돌린다 (0 = 비활성)."""
        if settings.auto_scale_down_after_s <= 0:
            return
        low_since: Optional[float] = None
        while True:
            await asyncio.sleep(1.0)
            sc = self.store.remediation.scale
            if sc and sc.status == "DONE" and self.store.queue.backlog_count < settings.backlog_threshold * 0.05:
                low_since = low_since or time.monotonic()
                if time.monotonic() - low_since >= settings.auto_scale_down_after_s:
                    await self.pool.scale_to(settings.base_workers)
                    self.store.remediation.scale = None
                    low_since = None
            else:
                low_since = None

    def reset(self) -> None:
        for t in list(self._tasks):
            t.cancel()
        self._tasks.clear()
        self._last_slack = float("-inf")
        r = self.store.remediation
        r.slack = r.scale = r.failover = None
