"""[Stage 4] Cloud Dataflow 워커 풀 & BigQuery 적재.

- 6개 Pod 슬롯(기본 2개 ACTIVE). 각 Pod 는 Route A 큐에서 배치 단위로 소비.
- 수집된 레코드는 Event-Time 기준으로 1초 텀블링 윈도 정렬 후 BigQuery Sink 로 적재.
- `scale_to(6)` 호출 시 STANDBY Pod 가 BOOTING → ACTIVE 로 순차 점등 (2 → 6, 3배).

Sink 추상화:
- MockBigQuerySink : 인메모리 링버퍼 (로컬 시연)
- GcpBigQuerySink  : google-cloud-bigquery `insert_rows_json` (USE_GCP=true)
"""
from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from collections import deque
from typing import Any, Optional

from config import settings
from models.schemas import PodState, WorkerPod
from models.timeseries import RateMeter
from pipeline.message_hub import MessageHub

log = logging.getLogger("dataflow")


# ════════════════════════════════════════════════════════════════
# BigQuery sinks
# ════════════════════════════════════════════════════════════════
class BigQuerySink(ABC):
    rows_written: int = 0

    @abstractmethod
    async def write(self, rows: list[dict[str, Any]]) -> None: ...

    def recent(self, n: int = 20) -> list[dict[str, Any]]:
        return []


class MockBigQuerySink(BigQuerySink):
    def __init__(self, keep: int = 2000) -> None:
        self.rows_written = 0
        self._rows: deque[dict[str, Any]] = deque(maxlen=keep)

    async def write(self, rows: list[dict[str, Any]]) -> None:
        self._rows.extend(rows)
        self.rows_written += len(rows)

    def recent(self, n: int = 20) -> list[dict[str, Any]]:
        return list(self._rows)[-n:]


class GcpBigQuerySink(BigQuerySink):  # pragma: no cover - requires GCP
    def __init__(self) -> None:
        from google.cloud import bigquery  # type: ignore

        self.rows_written = 0
        self._client = bigquery.Client(project=settings.gcp_project or None)
        self._table = settings.bq_table
        self._fallback = MockBigQuerySink()

    async def write(self, rows: list[dict[str, Any]]) -> None:
        await self._fallback.write(rows)
        errors = await asyncio.to_thread(self._client.insert_rows_json, self._table, rows)
        if errors:
            log.warning("BigQuery insert errors: %s", errors[:2])
        self.rows_written += len(rows)

    def recent(self, n: int = 20) -> list[dict[str, Any]]:
        return self._fallback.recent(n)


def build_sink() -> BigQuerySink:
    if settings.use_gcp:
        try:
            return GcpBigQuerySink()
        except Exception as exc:  # noqa: BLE001
            log.warning("BigQuery sink unavailable, using mock: %s", exc)
    return MockBigQuerySink()


# ════════════════════════════════════════════════════════════════
# Worker pool
# ════════════════════════════════════════════════════════════════
class _Pod:
    def __init__(self, index: int) -> None:
        self.index = index
        self.pod_id = f"dataflow-worker-{index + 1}"
        self.state = PodState.ACTIVE if index < settings.base_workers else PodState.STANDBY
        self.load_pct = 0.0
        self.processed = 0
        self.boosted = False

    def view(self) -> WorkerPod:
        return WorkerPod(
            pod_id=self.pod_id,
            index=self.index,
            state=self.state,
            load_pct=round(self.load_pct, 1),
            processed=self.processed,
            boosted=self.boosted,
        )


class DataflowWorkerPool:
    def __init__(self, hub: MessageHub, sink: Optional[BigQuerySink] = None) -> None:
        self.hub = hub
        self.sink = sink or build_sink()
        self.pods = [_Pod(i) for i in range(settings.max_workers)]
        self.meter = RateMeter(2.0)
        self._window: list[tuple[float, dict[str, Any]]] = []
        self._tasks: list[asyncio.Task] = []
        self._scale_task: Optional[asyncio.Task] = None
        self.target_workers = settings.base_workers

    # ── lifecycle ─────────────────────────────────────────────
    async def start(self) -> None:
        for pod in self.pods:
            self._tasks.append(asyncio.create_task(self._consume(pod), name=pod.pod_id))
        self._tasks.append(asyncio.create_task(self._flush_windows(), name="dataflow-window-flusher"))

    async def stop(self) -> None:
        for t in self._tasks:
            t.cancel()
        if self._scale_task:
            self._scale_task.cancel()

    # ── metrics ───────────────────────────────────────────────
    @property
    def active_workers(self) -> int:
        return sum(1 for p in self.pods if p.state == PodState.ACTIVE)

    @property
    def capacity_per_s(self) -> float:
        return settings.worker_batch_size / settings.worker_tick_s

    def views(self) -> list[WorkerPod]:
        return [p.view() for p in self.pods]

    # ── scaling ───────────────────────────────────────────────
    def scale_to(self, n: int) -> None:
        n = max(settings.base_workers, min(settings.max_workers, n))
        self.target_workers = n
        if self._scale_task and not self._scale_task.done():
            self._scale_task.cancel()
        self._scale_task = asyncio.create_task(self._apply_scale(n), name="dataflow-scale")

    async def _apply_scale(self, n: int) -> None:
        log.warning("SCALE workers → %d", n)
        for pod in self.pods:
            if pod.index < n and pod.state in (PodState.STANDBY, PodState.DRAINING):
                pod.state = PodState.BOOTING
                pod.boosted = pod.index >= settings.base_workers
                await asyncio.sleep(settings.pod_boot_stagger_s)
                pod.state = PodState.ACTIVE
        for pod in reversed(self.pods):
            if pod.index >= n and pod.state in (PodState.ACTIVE, PodState.BOOTING):
                pod.state = PodState.DRAINING
                await asyncio.sleep(0.25)
                pod.state = PodState.STANDBY
                pod.load_pct = 0.0
                pod.boosted = False

    # ── consumption ───────────────────────────────────────────
    async def _consume(self, pod: _Pod) -> None:
        tick = settings.worker_tick_s
        batch_size = settings.worker_batch_size
        # Pod 마다 위상을 살짝 다르게 → 자연스러운 처리 흐름
        await asyncio.sleep(tick * pod.index / settings.max_workers)
        while True:
            await asyncio.sleep(tick)
            if pod.state != PodState.ACTIVE:
                pod.load_pct = 0.0
                continue
            n = 0
            q = self.hub.route_a
            while n < batch_size:
                try:
                    msg = q.get_nowait()
                except asyncio.QueueEmpty:
                    break
                row = msg.model_dump(mode="json")
                row["_ingested_by"] = pod.pod_id
                self._window.append((msg.timestamp.timestamp(), row))
                n += 1
            pod.processed += n
            pod.load_pct = pod.load_pct * 0.5 + (n / batch_size * 100) * 0.5
            self.meter.mark(n)

    async def _flush_windows(self) -> None:
        """Event-Time 1초 텀블링 윈도 → 정렬 후 BigQuery 적재 (watermark 1s)."""
        while True:
            await asyncio.sleep(1.0)
            if not self._window:
                continue
            watermark = time.time() - 1.0
            ready = [w for w in self._window if w[0] <= watermark]
            if not ready:
                continue
            self._window = [w for w in self._window if w[0] > watermark]
            ready.sort(key=lambda w: w[0])
            try:
                await self.sink.write([r for _, r in ready])
            except Exception:  # noqa: BLE001
                log.exception("sink write failed")
