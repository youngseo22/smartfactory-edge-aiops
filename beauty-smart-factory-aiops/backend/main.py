"""FastAPI 엔트리포인트 — REST API · Ingestion WebSocket · Dashboard Broadcast.

Endpoints
- POST /api/scenario/{id}   : 장애 시나리오 트리거 (NORMAL | SCENARIO_1 | SCENARIO_2 | 0 | 1 | 2)
- GET  /api/snapshot        : 현재 대시보드 스냅샷
- GET  /api/health          : 헬스체크
- GET  /api/manual/search   : RAG 매뉴얼 검색 (?q=)
- GET  /api/bq/recent       : BigQuery(Mock) 최근 적재 로우
- WS   /ws/ingest           : Edge 센서 고속 수신 (단일 객체 / 리스트 / {uplink, messages})
- WS   /ws/dashboard        : 0.5초 주기 실시간 스냅샷 브로드캐스트

Run:  cd backend && uvicorn main:app --reload --port 8000
"""
from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from models.schemas import DashboardSnapshot, ScenarioId
from runtime import Platform

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s [%(name)s] %(message)s")
log = logging.getLogger("main")

SCENARIO_ALIASES = {
    "0": ScenarioId.NORMAL,
    "normal": ScenarioId.NORMAL,
    "1": ScenarioId.SCENARIO_1,
    "scenario_1": ScenarioId.SCENARIO_1,
    "s1": ScenarioId.SCENARIO_1,
    "2": ScenarioId.SCENARIO_2,
    "scenario_2": ScenarioId.SCENARIO_2,
    "s2": ScenarioId.SCENARIO_2,
}


# ════════════════════════════════════════════════════════════════
# Dashboard broadcaster (Step 3)
# ════════════════════════════════════════════════════════════════
class DashboardBroadcaster:
    """스냅샷을 0.5초마다 1회 생성해 모든 대시보드 클라이언트에 fan-out."""

    def __init__(self, platform: Platform) -> None:
        self.platform = platform
        self.clients: set[WebSocket] = set()
        self._task: Optional[asyncio.Task] = None
        self.last_payload: str = ""

    async def start(self) -> None:
        self._task = asyncio.create_task(self._loop(), name="dashboard-broadcast")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.clients.add(ws)
        if self.last_payload:
            await ws.send_text(self.last_payload)
        log.info("dashboard client connected (%d)", len(self.clients))

    def disconnect(self, ws: WebSocket) -> None:
        self.clients.discard(ws)
        log.info("dashboard client disconnected (%d)", len(self.clients))

    async def push_now(self) -> None:
        self.last_payload = self.platform.snapshot().model_dump_json()
        await self._fanout(self.last_payload)

    async def _fanout(self, payload: str) -> None:
        if not self.clients:
            return
        dead: list[WebSocket] = []
        results = await asyncio.gather(
            *(asyncio.wait_for(c.send_text(payload), timeout=1.0) for c in list(self.clients)),
            return_exceptions=True,
        )
        for client, res in zip(list(self.clients), results):
            if isinstance(res, Exception):
                dead.append(client)
        for d in dead:
            self.clients.discard(d)

    async def _loop(self) -> None:
        interval = settings.broadcast_interval_s
        while True:
            try:
                self.last_payload = self.platform.snapshot().model_dump_json()
                await self._fanout(self.last_payload)
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001
                log.exception("broadcast failed")
            await asyncio.sleep(interval)


platform = Platform()
broadcaster = DashboardBroadcaster(platform)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await platform.start()
    await broadcaster.start()
    yield
    await broadcaster.stop()
    await platform.stop()


app = FastAPI(title="AIOps Enterprise Monitoring Platform", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins) or ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ════════════════════════════════════════════════════════════════
# REST
# ════════════════════════════════════════════════════════════════
@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "mode": "GCP" if settings.use_gcp else "MOCK",
        "edge_transport": platform.transport_kind,
        "scenario": platform.scenario.value,
        "dashboard_clients": len(broadcaster.clients),
    }


@app.post("/api/scenario/{scenario_id}")
async def trigger_scenario(scenario_id: str) -> dict[str, Any]:
    key = scenario_id.strip()
    scenario = SCENARIO_ALIASES.get(key.lower())
    if scenario is None:
        try:
            scenario = ScenarioId(key.upper())
        except ValueError:
            raise HTTPException(404, f"unknown scenario '{scenario_id}'") from None
    platform.set_scenario(scenario)
    await broadcaster.push_now()
    return {"ok": True, "scenario": scenario.value}


@app.get("/api/snapshot", response_model=DashboardSnapshot)
async def snapshot() -> DashboardSnapshot:
    return platform.snapshot()


@app.get("/api/manual/search")
async def manual_search(q: str = Query(..., min_length=1), k: int = 3) -> list[dict[str, Any]]:
    hits = platform.rag.retriever.search(q, k=k)
    return [{"page": h.chunk["page"], "title": h.chunk["title"], "score": h.score} for h in hits]


@app.get("/api/bq/recent")
async def bq_recent(n: int = 20) -> dict[str, Any]:
    return {"rows_written": platform.workers.sink.rows_written, "rows": platform.workers.sink.recent(n)}


# ════════════════════════════════════════════════════════════════
# WebSockets
# ════════════════════════════════════════════════════════════════
@app.websocket("/ws/ingest")
async def ws_ingest(ws: WebSocket) -> None:
    """Edge → Gateway 고속 수신. ack 로 현재 라우팅 테이블을 회신."""
    await ws.accept()
    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except ValueError:
                continue
            uplink = "FACTORY"
            if isinstance(data, dict) and "messages" in data:
                uplink = data.get("uplink", "FACTORY")
                messages = data["messages"]
            elif isinstance(data, list):
                messages = data
            else:
                messages = [data]
                if isinstance(data, dict) and data.get("node_zone"):
                    uplink = platform.gateway.route_for(data["node_zone"])
            accepted = await platform.gateway.ingest_batch(messages, uplink=uplink)
            await ws.send_text(json.dumps({"accepted": accepted, "routing": platform.gateway.routing_table}))
    except WebSocketDisconnect:
        pass


@app.websocket("/ws/dashboard")
async def ws_dashboard(ws: WebSocket) -> None:
    await broadcaster.connect(ws)
    try:
        while True:
            # 클라이언트 → 서버 메시지로도 시나리오 전환 지원: {"scenario": "SCENARIO_1"}
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
                sid = SCENARIO_ALIASES.get(str(data.get("scenario", "")).lower()) or ScenarioId(
                    str(data.get("scenario", "")).upper()
                )
                platform.set_scenario(sid)
                await broadcaster.push_now()
            except (ValueError, AttributeError):
                continue
    except WebSocketDisconnect:
        pass
    finally:
        broadcaster.disconnect(ws)


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
