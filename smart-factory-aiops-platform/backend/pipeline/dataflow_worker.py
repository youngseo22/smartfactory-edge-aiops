"""Stage 4 — Dataflow 시뮬레이터: Event-Time 윈도잉/정렬 + BigQuery(iot_raw_logs) 적재 + 워커 동적 확장."""
from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional, Protocol

from config import TOPIC_RAW, settings
from models.schemas import utc_now_iso
from pipeline.message_hub import Broker
from state import StateStore

log = logging.getLogger("aiops.dataflow")


def _event_epoch(msg: dict) -> float:
    try:
        return datetime.fromisoformat(msg["timestamp"].replace("Z", "+00:00")).timestamp()
    except Exception:
        return datetime.now(timezone.utc).timestamp()


def to_row(msg: dict) -> dict:
    return {
        "sensor_id": msg.get("sensor_id"),
        "domain": msg.get("domain"),
        "node_zone": msg.get("node_zone"),
        "event_time": msg.get("timestamp"),
        "ingest_time": utc_now_iso(),
        "metrics": json.dumps(msg.get("metrics", {})),
        "status": msg.get("status"),
        "seq": msg.get("seq"),
    }


# ── 싱크 (BigQuery 추상화) ───────────────────────────────────
class Sink(Protocol):
    count: int

    async def write(self, rows: list[dict]) -> None: ...


class SqliteSink:
    """로컬 시연용 — 인메모리 SQLite 가 BigQuery `iot_raw_logs` 역할."""

    def __init__(self, path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS iot_raw_logs (
                   sensor_id TEXT, domain TEXT, node_zone TEXT, event_time TEXT,
                   ingest_time TEXT, metrics TEXT, status TEXT, seq INTEGER)"""
        )
        self.count = 0

    async def write(self, rows: list[dict]) -> None:
        if not rows:
            return
        self._conn.executemany(
            "INSERT INTO iot_raw_logs VALUES (:sensor_id,:domain,:node_zone,:event_time,"
            ":ingest_time,:metrics,:status,:seq)",
            rows,
        )
        self._conn.commit()
        self.count += len(rows)

    def query(self, sql: str) -> list[tuple]:
        return self._conn.execute(sql).fetchall()


class BigQuerySink:
    """실제 GCP — google-cloud-bigquery 스트리밍 insert."""

    def __init__(self) -> None:
        from google.cloud import bigquery  # lazy import

        self._client = bigquery.Client(project=settings.gcp_project)
        self._table = f"{settings.gcp_project}.{settings.bq_dataset}.{settings.bq_table}"
        self.count = 0

    async def write(self, rows: list[dict]) -> None:
        if not rows:
            return
        errors = await asyncio.to_thread(self._client.insert_rows_json, self._table, rows)
        if errors:
            log.error("BigQuery insert errors: %s", errors[:3])
        else:
            self.count += len(rows)


def make_sink() -> Sink:
    if settings.use_gcp:
        try:
            return BigQuerySink()
        except Exception:
            log.exception("BigQuery 초기화 실패 → SQLite 싱크로 대체")
    return SqliteSink()


# ── Event-Time 윈도우 ───────────────────────────────────────
class EventTimeWindower:
    """이벤트 발생 시각 기준 고정 윈도우(1s). 워터마크가 지난 윈도우만 시간순 정렬해 배출."""

    def __init__(self, window_s: float, allowed_lateness_s: float) -> None:
        self.window_s = window_s
        self.lateness = allowed_lateness_s
        self._w: dict[int, list[dict]] = defaultdict(list)

    def add(self, msg: dict) -> None:
        self._w[int(_event_epoch(msg) // self.window_s)].append(msg)

    def pop_closed(self, now_epoch: Optional[float] = None, flush_all: bool = False) -> list[dict]:
        now = now_epoch if now_epoch is not None else datetime.now(timezone.utc).timestamp()
        watermark = now - self.lateness
        keys = sorted(k for k in self._w if flush_all or (k + 1) * self.window_s <= watermark)
        out: list[dict] = []
        for k in keys:
            out.extend(sorted(self._w.pop(k), key=_event_epoch))
        return out


# ── 워커 풀 ────────────────────────────────────────────────
class DataflowWorkerPool:
    def __init__(self, store: StateStore, broker: Broker, sink: Sink) -> None:
        self.store = store
        self.broker = broker
        self.sink = sink
        self.windower = EventTimeWindower(settings.window_s, settings.allowed_lateness_s)
        self._workers: dict[int, asyncio.Task] = {}
        self._flusher: Optional[asyncio.Task] = None
        self._gen = 0  # reset 시 진행 중인 scale_to 중단용

    async def start(self) -> None:
        for wid in range(1, settings.base_workers + 1):
            self._spawn(wid)
        self._flusher = asyncio.create_task(self._flush_loop())

    async def stop(self) -> None:
        for t in [*self._workers.values(), *([self._flusher] if self._flusher else [])]:
            t.cancel()
        await asyncio.gather(*self._workers.values(), return_exceptions=True)
        await self._flush(all_=True)

    def _spawn(self, wid: int) -> None:
        self.store.worker_pods[wid - 1].status = "ACTIVE"
        self._workers[wid] = asyncio.create_task(self._consume(wid))

    def _despawn(self, wid: int) -> None:
        task = self._workers.pop(wid, None)
        if task:
            task.cancel()
        pod = self.store.worker_pods[wid - 1]
        pod.status, pod.load_pct = "STANDBY", 0

    # ── CONTAINER_SCALE_UP: 2 → 6 (순차 점등) ───────────────
    async def scale_to(self, n: int) -> None:
        n = max(1, min(settings.max_workers, n))
        gen = self._gen
        for wid in range(1, n + 1):
            if wid in self._workers:
                continue
            self.store.worker_pods[wid - 1].status = "STARTING"
            await asyncio.sleep(settings.worker_start_stagger_s)
            if gen != self._gen:
                return
            self._spawn(wid)
        # 2. Scale-Down: 6 → 2 점진적 순차 회수 (Graceful Staggered Drain)
        to_remove = [wid for wid in sorted(self._workers, reverse=True) if wid > n]
        for wid in to_remove:
            if gen != self._gen:
                return
            pod = self.store.worker_pods[wid - 1]
            pod.status = "TERMINATING"
            pod.load_pct = max(0, pod.load_pct // 2)
            await asyncio.sleep(settings.worker_start_stagger_s)
            if gen != self._gen:
                return
            self._despawn(wid)

    def reset(self) -> None:
        self._gen += 1
        for wid in sorted(self._workers, reverse=True):
            if wid > settings.base_workers:
                self._despawn(wid)
        for pod in self.store.worker_pods:
            if pod.id > settings.base_workers:
                pod.status, pod.load_pct = "STANDBY", 0

    async def _consume(self, wid: int) -> None:
        pod = self.store.worker_pods[wid - 1]
        ema = 0.0
        try:
            while True:
                msgs = await self.broker.pull(TOPIC_RAW, settings.worker_batch)
                for m in msgs:
                    self.windower.add(m)
                if msgs:
                    self.store.meters.drain.add(len(msgs))
                ema = 0.7 * ema + 0.3 * (len(msgs) / settings.worker_batch)
                pod.load_pct = int(ema * 100)
                await asyncio.sleep(settings.worker_tick_s)
        except asyncio.CancelledError:
            pod.load_pct = 0
            raise

    async def _flush_loop(self) -> None:
        while True:
            await asyncio.sleep(1.0)
            await self._flush()

    async def _flush(self, all_: bool = False) -> None:
        msgs = self.windower.pop_closed(flush_all=all_)
        if not msgs:
            return
        rows = [to_row(m) for m in msgs]
        for i in range(0, len(rows), 500):
            await self.sink.write(rows[i : i + 500])
        self.store.meters.bq.add(len(rows))
