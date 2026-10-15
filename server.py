import asyncio
import json
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

# ⚡ [최신 FastAPI 표준] lifespan을 이용한 백그라운드 큐 워커 구동
@asynccontextmanager
async def lifespan(app: FastAPI):
    async def pubsub_fanout_worker():
        while True:
            item = await message_queue.get()
            stats["queue_backlog"] = message_queue.qsize()
            
            device_id = item["device_id"]
            payload = item["payload"]
            
            server_time = datetime.now(timezone.utc)
            try:
                event_time = datetime.fromisoformat(payload["event_time"].replace("Z", "+00:00"))
                delay_sec = (server_time.replace(tzinfo=None) - event_time.replace(tzinfo=None)).total_seconds()
            except Exception:
                delay_sec = 0.0

            if delay_sec > 1.5:
                stats["late_data"] += 1

            # Route A: 전체 로그 파이프라인 시뮬레이션
            stats["route_a_processed"] += 1

            # Route B: AI Agent 긴급 호출 필터링
            if payload.get("status") == "WARNING":
                stats["route_b_warnings"] += 1
                log_msg = f"🚨 [Route B 긴급] AI Agent 호출 | 기기: {device_id} | SVM: {payload['svm']}"
                add_log(log_msg)

            message_queue.task_done()

    asyncio.create_task(pubsub_fanout_worker())
    yield

app = FastAPI(lifespan=lifespan)

# ⚡ Cloud Pub/Sub 역할을 할 비동기 메시지 큐
message_queue = asyncio.Queue()

# 실시간 통계 및 최근 로그
active_connections: set[WebSocket] = set()
stats = {
    "total_messages": 0,
    "queue_backlog": 0,
    "route_a_processed": 0,
    "route_b_warnings": 0,
    "late_data": 0,
    "reconnections": 0
}
recent_logs = []

# 📊 관제 대시보드 HTML + JS UI
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>아모레 스마트 팩토리 - Pub/Sub 아키텍처 관제</title>
    <style>
        body { font-family: -apple-system, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 25px; }
        .header-container { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        h1 { font-size: 24px; margin: 0; color: #38bdf8; }
        p { color: #94a3b8; margin: 5px 0 0 0; }
        .reset-btn { background: #f43f5e; color: white; border: none; padding: 10px 20px; font-size: 14px; font-weight: bold; border-radius: 8px; cursor: pointer; transition: background 0.2s; }
        .reset-btn:hover { background: #e11d48; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 25px; }
        .card { background: #1e293b; border-radius: 12px; padding: 18px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); border: 1px solid #334155; }
        .card-title { font-size: 13px; color: #94a3b8; font-weight: bold; }
        .card-value { font-size: 28px; font-weight: bold; margin-top: 8px; color: #f1f5f9; }
        .pubsub-card { border-color: #f59e0b; background: #1e293b; }
        .warning-val { color: #f43f5e !important; }
        .log-box { background: #1e293b; border-radius: 12px; padding: 20px; border: 1px solid #334155; height: 230px; overflow-y: auto; font-family: monospace; font-size: 13px; }
        .log-item { margin-bottom: 8px; border-bottom: 1px solid #334155; padding-bottom: 4px; }
        .log-warn { color: #f43f5e; font-weight: bold; }
    </style>
</head>
<body>
    <div class="header-container">
        <div>
            <h1>🏭 Smart Factory AIOps Control Center (Pub/Sub Hub)</h1>
            <p>GKE Gateway ➔ Cloud Pub/Sub Queue-Based Load Leveling & Fan-out</p>
        </div>
        <button class="reset-btn" onclick="resetStats()">🔄 통계 초기화 (Reset)</button>
    </div>

    <div class="grid">
        <div class="card">
            <div class="card-title">활성 WebSocket 연결</div>
            <div class="card-value" id="conns">0</div>
        </div>
        <div class="card pubsub-card">
            <div class="card-title">⚡ Pub/Sub 큐 적체량</div>
            <div class="card-value" id="backlog" style="color: #fbbf24;">0</div>
        </div>
        <div class="card">
            <div class="card-title">Route A (전체 로그 처리)</div>
            <div class="card-value" id="routeA">0</div>
        </div>
        <div class="card">
            <div class="card-title">🚨 Route B (AI 에이전트 경고)</div>
            <div class="card-value warning-val" id="routeB">0</div>
        </div>
    </div>

    <div class="card">
        <div class="card-title" style="margin-bottom: 10px;">실시간 Fan-out 및 장애 대응 로그 브리프</div>
        <div class="log-box" id="logBox">
            <div class="log-item">시스템 대시보드 연결 완료. Pub/Sub 허브 가동 중...</div>
        </div>
    </div>

    <script>
        const ws = new WebSocket(`ws://${location.host}/ws-dashboard`);
        
        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            document.getElementById('conns').innerText = data.connections;
            document.getElementById('backlog').innerText = data.queue_backlog;
            document.getElementById('routeA').innerText = data.route_a_processed;
            document.getElementById('routeB').innerText = data.route_b_warnings;

            const logBox = document.getElementById('logBox');
            logBox.innerHTML = data.logs.map(log => 
                `<div class="log-item ${log.includes('긴급') || log.includes('이상') ? 'log-warn' : ''}">${log}</div>`
            ).join('');
            logBox.scrollTop = logBox.scrollHeight;
        };

        function resetStats() {
            fetch('/reset', { method: 'POST' });
        }
    </script>
</body>
</html>
"""

@app.get("/")
async def get_dashboard():
    return HTMLResponse(DASHBOARD_HTML)

@app.post("/reset")
async def reset_statistics():
    global stats, recent_logs
    stats = {
        "total_messages": 0,
        "queue_backlog": 0,
        "route_a_processed": 0,
        "route_b_warnings": 0,
        "late_data": 0,
        "reconnections": 0
    }
    recent_logs = [f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 큐 및 통계 데이터 초기화 완료"]
    return {"status": "success"}

def add_log(msg: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    recent_logs.append(f"[{timestamp}] {msg}")

dashboard_clients: set[WebSocket] = set()

@app.websocket("/ws-dashboard")
async def dashboard_ws(websocket: WebSocket):
    await websocket.accept()
    dashboard_clients.add(websocket)
    try:
        while True:
            await asyncio.sleep(0.4)
            stats["queue_backlog"] = message_queue.qsize()
            payload = {
                "connections": len(active_connections),
                "queue_backlog": stats["queue_backlog"],
                "route_a_processed": stats["route_a_processed"],
                "route_b_warnings": stats["route_b_warnings"],
                "logs": recent_logs[-15:]
            }
            await websocket.send_text(json.dumps(payload))
    except WebSocketDisconnect:
        pass
    finally:
        dashboard_clients.discard(websocket)

@app.websocket("/ws/{device_id}")
async def sensor_endpoint(websocket: WebSocket, device_id: str):
    await websocket.accept()
    active_connections.add(websocket)
    try:
        while True:
            raw_data = await websocket.receive_text()
            payload = json.loads(raw_data)
            stats["total_messages"] += 1

            # Pub/Sub 큐에 즉시 푸시 (Load Leveling)
            await message_queue.put({"device_id": device_id, "payload": payload})
            stats["queue_backlog"] = message_queue.qsize()

    except WebSocketDisconnect:
        stats["reconnections"] += 1
        add_log(f"⚠️ [연결 끊김] 기기: {device_id}")
    finally:
        active_connections.discard(websocket)

if __name__ == "__main__":
    import uvicorn
    print("🚀 스마트 팩토리 Pub/Sub 아키텍처 서버 시작 (포트: 8000)")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")