"""FastAPI 엔트리포인트 — REST / WebSocket 게이트웨이 / 대시보드 브로드캐스트.

실행:  cd backend && uvicorn main:app --reload --port 8000
"""
from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from runtime import Platform

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("aiops.main")


class DashboardBroadcaster:
    """0.5초 주기로 모든 /ws/dashboard 클라이언트에 스냅샷 전송."""

    def __init__(self, platform: Platform) -> None:
        self.platform = platform
        self.clients: set[WebSocket] = set()

    async def run(self) -> None:
        while True:
            await asyncio.sleep(settings.broadcast_interval_s)
            if not self.clients:
                continue
            payload = self.platform.snapshot().model_dump_json()
            results = await asyncio.gather(
                *(self._send(ws, payload) for ws in list(self.clients)), return_exceptions=True
            )
            for ws, ok in zip(list(self.clients), results):
                if ok is not True:
                    self.clients.discard(ws)

    @staticmethod
    async def _send(ws: WebSocket, payload: str) -> bool:
        await ws.send_text(payload)
        return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    platform = Platform()
    broadcaster = DashboardBroadcaster(platform)
    app.state.platform = platform
    app.state.broadcaster = broadcaster
    await platform.start()
    task = asyncio.create_task(broadcaster.run())
    try:
        yield
    finally:
        task.cancel()
        await platform.stop()


app = FastAPI(title="Smart Factory AIOps Platform", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/api/health")
async def health():
    return {"ok": True, "mode": settings.mode, "edge_transport": settings.edge_transport}


@app.get("/api/state")
async def state():
    return app.state.platform.snapshot()


@app.post("/api/scenario/{scenario_id}")
async def trigger_scenario(scenario_id: int):
    """0 = Normal · 1 = 모터 불량 · 2 = 콜드체인 이상 · 3 = 주문 폭증 · 4 = 모터 교체 · 5 = Zone A 복구 · 6 = 라인 진동(벨트 급가속) · 7 = 라인 안정화"""
    if scenario_id not in (0, 1, 2, 3, 4, 5, 6, 7):
        raise HTTPException(status_code=404, detail="scenario must be between 0 and 7")
    active = await app.state.platform.apply_scenario(scenario_id)
    return {"ok": True, "scenario": scenario_id, "active": active}


@app.post("/api/motor/svm/step")
async def step_motor_svm(delta: float = 1.5):
    """SVM 진동치를 delta(기본 1.5)만큼 증가/감소. 7.0 초과 시 자동 인터록 발동."""
    val = await app.state.platform.step_motor_svm(delta)
    return {"ok": True, "svm": val, "active": sorted(app.state.platform.store.active_scenarios)}


@app.websocket("/ws/ingest")
async def ws_ingest(ws: WebSocket):
    """Edge → Gateway 고속 수신 (단건 dict 또는 dict 배열)."""
    await ws.accept()
    gateway = app.state.platform.gateway
    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                gateway.dropped += 1
                continue
            for item in data if isinstance(data, list) else [data]:
                await gateway.ingest(item)
    except WebSocketDisconnect:
        pass


@app.websocket("/ws/dashboard")
async def ws_dashboard(ws: WebSocket):
    await ws.accept()
    broadcaster: DashboardBroadcaster = app.state.broadcaster
    broadcaster.clients.add(ws)
    try:
        await ws.send_text(app.state.platform.snapshot().model_dump_json())  # 접속 즉시 1회
        while True:
            await ws.receive_text()  # 연결 유지/종료 감지
    except WebSocketDisconnect:
        pass
    finally:
        broadcaster.clients.discard(ws)
