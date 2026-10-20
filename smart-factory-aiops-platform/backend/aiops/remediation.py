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
            "text": f"🚨 [{card.severity}] {card.cause}\n🔧 SOP 조치: {card.key_action} (매뉴얼 p.{card.manual_page})\n📊 진단 신뢰도: {int(card.confidence * 100)}%",
        }, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(settings.slack_webhook_url, body, {"Content-Type": "application/json; charset=utf-8"})
        try:
            await asyncio.to_thread(urllib.request.urlopen, req, None, 5)
        except Exception:
            log.exception("Slack webhook 전송 실패")


class Remediator:
    """3대 자율 대응 실행기."""

    def __init__(self, store: StateStore, rag: RagAgent, notifier: SlackNotifier,
                 pool: DataflowWorkerPool, gateway: IngestionGateway) -> None:
        self.store, self.rag, self.notifier, self.pool, self.gateway = store, rag, notifier, pool, gateway

    # [Action A] SLACK_ALERT — 로컬 RAG 로 즉시 알림 반영(0.01초) 후 Vertex AI 로 백그라운드 보강
    async def slack_alert(self, event: AlertEvent) -> None:
        m = self.store.motor
        ctx = {"svm": m.svm, "torque_nm": m.torque_nm, "rpm": m.rpm, "event_type": event.type}
        if event.zone:
            ctx["zone"] = event.zone

        # 1. Fast Path: 로컬 지식베이스(BM25) 즉각 검색 (1ms 이내)
        if hasattr(self.rag, "diagnose_local"):
            diag = self.rag.diagnose_local(event, ctx)
        else:
            diag = await self.rag.diagnose(event, ctx)

        val = event.value if event.value is not None else (m.svm if event.type == "VIBRATION_HIGH" else 0.0)
        ch = (
            "#aiops-capping-line" if event.type == "VIBRATION_HIGH"
            else "#aiops-conveyor-line" if event.type == "CONVEYOR_ANOMALY"
            else "#aiops-coldchain-zone"
        )
        card = SlackCard(
            channel=ch,
            severity="CRIT" if event.type in ("VIBRATION_HIGH", "NODE_DOWN") else "WARN",
            manual_page=diag.manual_page, manual_title=diag.manual_title,
            key_action=diag.key_action, cause=diag.cause, confidence=diag.confidence,
            svm=round(val, 1), ts=epoch_ms(),
        )
        # 즉시 상태 저장 및 프론트엔드/관리자 알림 트리거
        self.store.remediation.slack = card
        self.store.push_event("ACTION_SLACK")
        await self.notifier.send(card)

        # 2. Async Path: Vertex AI (Gemini) 모델이 있는 경우 비동기 백그라운드로 보강
        if hasattr(self.rag, "enrich_with_gemini"):
            asyncio.create_task(self._enrich_slack_card(card, diag, event, ctx, ch))

    async def _enrich_slack_card(self, original_card: SlackCard, base_diag, event: AlertEvent, ctx: dict, ch: str) -> None:
        try:
            enriched = await self.rag.enrich_with_gemini(base_diag, event, ctx)
            current = self.store.remediation.slack
            # 여전히 동일 채널/장애의 카드인 경우 최신 LLM 진단 결과로 보강 업데이트
            if current and current.channel == ch:
                updated_card = original_card.model_copy(update={
                    "cause": enriched.cause,
                    "confidence": enriched.confidence,
                })
                self.store.remediation.slack = updated_card
        except Exception:
            log.warning("Async Gemini enrichment skipped or failed")

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
        self._last_slack_by_type: dict[str, float] = {}

    def _spawn(self, coro: Coroutine) -> None:
        t = asyncio.create_task(coro)
        self._tasks.add(t)
        t.add_done_callback(self._on_done)

    def _on_done(self, t: asyncio.Task) -> None:
        self._tasks.discard(t)
        if not t.cancelled() and t.exception():
            log.error("remediation action failed", exc_info=t.exception())

    async def dispatch_now(self, ev: AlertEvent) -> None:
        rem = self.store.remediation
        now = time.monotonic()
        last = self._last_slack_by_type.get(ev.type, float("-inf"))

        # 1. 캡핑 모터 진동 과부하
        if ev.type == "VIBRATION_HIGH":
            if now - last > 30.0:
                self._last_slack_by_type[ev.type] = now
                await self.rem.slack_alert(ev)
        # 2. 컨베이어 인버터 이상 및 라인 진동
        elif ev.type == "CONVEYOR_ANOMALY":
            if now - last > 30.0:
                self._last_slack_by_type[ev.type] = now
                await self.rem.slack_alert(ev)
        # 3. 큐 백로그 급증
        elif ev.type == "BACKLOG_HIGH":
            if not (rem.scale and rem.scale.status == "RUNNING"):
                await self.rem.scale_up(ev)
        # 4. 콜드체인 노드 단절 및 과온
        elif ev.type in ("NODE_DOWN", "TEMP_HIGH"):
            if ev.type == "NODE_DOWN" and ev.zone and ev.zone == self.store.routing.active_zone:
                await self.rem.node_failover(ev)
            if now - last > 30.0:
                self._last_slack_by_type[ev.type] = now
                await self.rem.slack_alert(ev)

    def _dispatch(self, ev: AlertEvent) -> None:
        self._spawn(self.dispatch_now(ev))

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
                    self.store.active_scenarios.discard(3)
                    self.store.remove_events("BACKLOG_HIGH", "ACTION_SCALE")
                    low_since = None
            else:
                low_since = None

    def reset(self) -> None:
        for t in list(self._tasks):
            t.cancel()
        self._tasks.clear()
        self._last_slack_by_type.clear()
        r = self.store.remediation
        r.slack = r.scale = r.failover = None
