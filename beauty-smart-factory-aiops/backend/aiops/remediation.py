"""[Stage 5] AIOps Engine — 3대 자율 대응 실행기.

Route B 이벤트 → RAG 진단 → 자율 대응:
- Action A · SLACK_ALERT         : 매뉴얼 근거(p.42 등) 미니 카드 / Slack Webhook 발송
- Action B · CONTAINER_SCALE_UP  : Dataflow 워커 Pod 2 → 6 (3배) 확장, 안정화 후 자동 축소
- Action C · NODE_FAILOVER       : 게이트웨이 라우팅 ZONE_A → ZONE_B 전환
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from typing import Callable, Optional

from aiops.rag_agent import Diagnosis, RagAgent
from config import settings
from models.schemas import (
    ActionRecord,
    ActionType,
    EventType,
    FailoverWidget,
    PipelineEvent,
    RemediationState,
    ScaleUpWidget,
    SensorStatus,
    SlackCard,
)
from pipeline.dataflow_worker import DataflowWorkerPool
from pipeline.gateway import IngestionGateway
from pipeline.message_hub import MessageHub

log = logging.getLogger("aiops")


class SlackNotifier:
    """Slack Incoming Webhook (SLACK_WEBHOOK_URL 설정 시 실제 발송)."""

    async def send(self, card: SlackCard) -> bool:
        if not settings.slack_webhook_url:
            return False
        try:
            import httpx

            blocks = {
                "text": f":rotating_light: {card.title}",
                "blocks": [
                    {"type": "header", "text": {"type": "plain_text", "text": f"🚨 {card.metric}"}},
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*📖 Manual*\n{card.page}"},
                            {"type": "mrkdwn", "text": f"*🔧 Action*\n{card.keyword}"},
                        ],
                    },
                ],
            }
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.post(settings.slack_webhook_url, json=blocks)
                return r.status_code < 300
        except Exception as exc:  # noqa: BLE001
            log.warning("slack send failed: %s", exc)
            return False


class AIOpsEngine:
    def __init__(
        self,
        hub: MessageHub,
        gateway: IngestionGateway,
        workers: DataflowWorkerPool,
        rag: Optional[RagAgent] = None,
        loss_fn: Optional[Callable[[], tuple[float, int]]] = None,
    ) -> None:
        self.hub = hub
        self.gateway = gateway
        self.workers = workers
        self.rag = rag or RagAgent()
        self.slack_notifier = SlackNotifier()
        self.loss_fn = loss_fn or (lambda: (0.0, 0))

        self.slack = SlackCard()
        self.scale_up = ScaleUpWidget(from_pods=settings.base_workers, to_pods=settings.base_workers)
        self.failover = FailoverWidget()
        self.actions: deque[ActionRecord] = deque(maxlen=14)
        self.ai_events = 0
        self._incidents: set[tuple[str, str]] = set()
        self._task: Optional[asyncio.Task] = None
        self._scale_watch: Optional[asyncio.Task] = None
        self._generation = 0  # reset 시 진행 중 대응 무효화

    # ── lifecycle ─────────────────────────────────────────────
    async def start(self) -> None:
        self._task = asyncio.create_task(self._run(), name="aiops-engine")

    async def stop(self) -> None:
        for t in (self._task, self._scale_watch):
            if t:
                t.cancel()

    def reset(self) -> None:
        self._generation += 1
        self._incidents.clear()
        self.slack = SlackCard()
        self.failover = FailoverWidget()
        self.scale_up = ScaleUpWidget(from_pods=settings.base_workers, to_pods=settings.base_workers)
        if self._scale_watch:
            self._scale_watch.cancel()
            self._scale_watch = None
        while not self.hub.route_b.empty():
            self.hub.route_b.get_nowait()

    def state(self) -> RemediationState:
        self.scale_up.active_pods = self.workers.active_workers
        self.scale_up.throughput_pct = round(self.workers.active_workers / settings.base_workers * 100)
        if self.failover.active:
            loss, recovered = self.loss_fn()
            self.failover.data_loss_pct = loss
            self.failover.recovered_msgs = recovered
        return RemediationState(slack=self.slack, scale_up=self.scale_up, failover=self.failover)

    def _record(self, action: ActionType, target: str, **meta) -> None:
        self.actions.append(ActionRecord(action=action, target=target, ts=time.time(), meta=meta))

    # ── event loop ────────────────────────────────────────────
    async def _run(self) -> None:
        while True:
            event = await self.hub.route_b.get()
            self.ai_events += 1
            key = (event.event_type.value, event.source)
            if key in self._incidents:
                continue  # 이미 대응 중인 인시던트
            self._incidents.add(key)
            asyncio.create_task(self._handle(event, self._generation))

    async def _handle(self, event: PipelineEvent, gen: int) -> None:
        try:
            await asyncio.sleep(settings.ai_diagnosis_delay_s)  # 진단 레이턴시 연출
            diag = await self.rag.diagnose(event)
            if gen != self._generation:
                return
            log.warning("DIAG %s/%s → %s %s", event.event_type.value, event.source, diag.page, diag.keyword)
            et = event.event_type
            if et == EventType.VIBRATION_ANOMALY:
                await self.action_slack(event, diag)
            elif et == EventType.BACKLOG_HIGH:
                self.action_scale_up(event, diag)
            elif et == EventType.NODE_DOWN:
                self.action_failover(event, diag)
                await self.action_slack(event, diag)
            elif et == EventType.TEMP_HIGH:
                self._record(ActionType.DIAGNOSIS, event.source, page=diag.page, keyword=diag.keyword)
        except Exception:  # noqa: BLE001
            log.exception("remediation failed")
            self._incidents.discard((event.event_type.value, event.source))

    # ── Action A ──────────────────────────────────────────────
    async def action_slack(self, event: PipelineEvent, diag: Diagnosis) -> None:
        self.slack = SlackCard(
            active=True,
            page=diag.page,
            title=diag.title,
            keyword=diag.keyword,
            metric=diag.metric,
            severity=event.severity,
            source=diag.source,  # type: ignore[arg-type]
            confidence=diag.confidence,
            ts=time.time(),
        )
        self._record(ActionType.SLACK_ALERT, event.source, page=diag.page, keyword=diag.keyword)
        self.slack.delivered = await self.slack_notifier.send(self.slack)

    # ── Action B ──────────────────────────────────────────────
    def action_scale_up(self, event: PipelineEvent, diag: Diagnosis) -> None:
        before = self.workers.active_workers
        self.workers.scale_to(settings.max_workers)
        self.scale_up = ScaleUpWidget(
            active=True,
            from_pods=before,
            to_pods=settings.max_workers,
            active_pods=before,
            throughput_pct=round(before / settings.base_workers * 100),
            ts=time.time(),
        )
        self._record(
            ActionType.CONTAINER_SCALE_UP,
            "dataflow-workers",
            backlog=event.payload.get("backlog_count"),
            pods=f"{before}->{settings.max_workers}",
        )
        if self._scale_watch:
            self._scale_watch.cancel()
        self._scale_watch = asyncio.create_task(self._watch_scale_down(event))

    async def _watch_scale_down(self, event: PipelineEvent) -> None:
        """유입량이 기본 용량 70% 이하 & 백로그 50 미만이 8초 지속되면 축소."""
        calm = 0
        base_capacity = settings.base_workers * self.workers.capacity_per_s
        while True:
            await asyncio.sleep(1.0)
            ingress = self.gateway.meter.rate()
            if ingress <= base_capacity * 0.7 and self.hub.backlog_count < 50:
                calm += 1
            else:
                calm = 0
            if calm >= 8:
                self.workers.scale_to(settings.base_workers)
                self.scale_up.active = False
                self._record(ActionType.CONTAINER_SCALE_DOWN, "dataflow-workers", pods=f"{settings.max_workers}->{settings.base_workers}")
                self._incidents.discard((event.event_type.value, event.source))
                return

    # ── Action C ──────────────────────────────────────────────
    def action_failover(self, event: PipelineEvent, diag: Diagnosis) -> None:
        zone = event.source
        backup = event.payload.get("backup", "ZONE_B")
        self.gateway.failover(zone, backup)
        self.failover = FailoverWidget(active=True, from_zone=zone, to_zone=backup, ts=time.time())
        self._record(ActionType.NODE_FAILOVER, zone, to=backup)

    def severity_of(self) -> SensorStatus:
        return self.slack.severity
