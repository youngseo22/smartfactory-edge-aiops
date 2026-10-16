import asyncio
import json
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

message_queue = asyncio.Queue()
active_connections: set[WebSocket] = set()

# --- [1~3단계 관련 상태 데이터] ---
stats = {
    "total_messages": 0,
    "queue_backlog": 0,
    "route_a_processed": 0,
    "route_b_warnings": 0,
    "late_data": 0,
    "reconnections": 0
}
recent_logs = []

# --- [4단계 관련 상태 데이터] ---
pipeline_stats = {
    "raw_incoming": 0,
    "sorted_processed": 0,
    "bq_stored_count": 0,
    "late_recovered": 0
}
bigquery_storage = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    async def background_unified_worker():
        while True:
            item = await message_queue.get()
            stats["queue_backlog"] = message_queue.qsize()
            
            device_id = item["device_id"]
            payload = item["payload"]
            
            # --- 1~3단계 로직 처리 ---
            server_time = datetime.now(timezone.utc)
            try:
                event_time = datetime.fromisoformat(payload["event_time"].replace("Z", "+00:00"))
                delay_sec = (server_time.replace(tzinfo=None) - event_time.replace(tzinfo=None)).total_seconds()
            except Exception:
                delay_sec = 0.0

            if delay_sec > 1.5:
                stats["late_data"] += 1

            stats["route_a_processed"] += 1

            if payload.get("status") == "WARNING":
                stats["route_b_warnings"] += 1
                log_msg = f"🚨 [Route B 긴급] AI Agent 호출 | 기기: {device_id} | SVM: {payload['svm']}"
                recent_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {log_msg}")
                if len(recent_logs) > 20:
                    recent_logs.pop(0)

            # --- 4단계 (Dataflow & BigQuery) 로직 처리 ---
            pipeline_stats["raw_incoming"] += 1
            if delay_sec > 1.0:
                pipeline_stats["late_recovered"] += 1

            pipeline_stats["sorted_processed"] += 1
            pipeline_stats["bq_stored_count"] += 1
            
            stored_record = {
                "device_id": device_id,
                "event_time": payload["event_time"],
                "svm": payload["svm"],
                "status": payload["status"],
                "delay_sec": round(delay_sec, 2)
            }
            bigquery_storage.append(stored_record)
            if len(bigquery_storage) > 50:
                bigquery_storage.pop(0)

            message_queue.task_done()

    asyncio.create_task(background_unified_worker())
    yield

app = FastAPI(lifespan=lifespan)

# ==========================================
# 📊 HTML 1: 1~3단계 통합 관제 대시보드 ( / )
# ==========================================
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>스마트 팩토리 - 1~3단계 통합 관제</title>
    <style>
        body { font-family: -apple-system, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 25px; }
        .header-container { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        h1 { font-size: 24px; margin: 0; color: #38bdf8; }
        p { color: #94a3b8; margin: 5px 0 0 0; }
        .nav-link { background: #10b981; color: white; text-decoration: none; padding: 10px 18px; border-radius: 8px; font-size: 14px; font-weight: bold; }
        .nav-link:hover { background: #059669; }
        .reset-btn { background: #f43f5e; color: white; border: none; padding: 10px 20px; font-size: 14px; font-weight: bold; border-radius: 8px; cursor: pointer; transition: background 0.2s; }
        .reset-btn:hover { background: #e11d48; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 25px; }
        .card { background: #1e293b; border-radius: 12px; padding: 18px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); border: 1px solid #334155; }
        .card-title { font-size: 13px; color: #94a3b8; font-weight: bold; }
        .card-value { font-size: 28px; font-weight: bold; margin-top: 8px; color: #f1f5f9; }
        .pubsub-card { border-color: #f59e0b; }
        .warning-val { color: #f43f5e !important; }
        .log-box { background: #1e293b; border-radius: 12px; padding: 20px; border: 1px solid #334155; height: 230px; overflow-y: auto; font-family: monospace; font-size: 13px; }
        .log-item { margin-bottom: 8px; border-bottom: 1px solid #334155; padding-bottom: 4px; }
        .log-warn { color: #f43f5e; font-weight: bold; }
    </style>
</head>
<body>
    <div class="header-container">
        <div>
            <h1>🏭 Step 1~3: Gateway & Pub/Sub Hub</h1>
            <p>WebSocket 다중 부하 수용 및 큐 기반 부하 평준화 (Fan-out)</p>
        </div>
        <div style="display: flex; gap: 10px; align-items: center;">
            <a href="/pipeline" class="nav-link">👉 4단계 파이프라인 대시보드 이동</a>
            <button class="reset-btn" onclick="resetStats()">🔄 통계 초기화</button>
        </div>
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

# ==========================================
# 📊 HTML 2: 4단계 파이프라인 대시보드 ( /pipeline )
# ==========================================
PIPELINE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>스마트 팩토리 - 4단계 파이프라인</title>
    <style>
        body { font-family: -apple-system, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 25px; }
        .header-container { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        h1 { font-size: 24px; margin: 0; color: #10b981; }
        p { color: #94a3b8; margin: 5px 0 0 0; }
        .nav-link { background: #334155; color: white; text-decoration: none; padding: 10px 18px; border-radius: 8px; font-size: 14px; font-weight: bold; }
        .nav-link:hover { background: #475569; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px; margin-bottom: 25px; }
        .card { background: #1e293b; border-radius: 12px; padding: 18px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); border: 1px solid #334155; }
        .card-title { font-size: 13px; color: #94a3b8; font-weight: bold; }
        .card-value { font-size: 28px; font-weight: bold; margin-top: 8px; color: #f1f5f9; }
        .table-box { background: #1e293b; border-radius: 12px; padding: 20px; border: 1px solid #334155; height: 260px; overflow-y: auto; font-family: monospace; font-size: 12px; }
        table { width: 100%; border-collapse: collapse; text-align: left; }
        th, td { padding: 8px 12px; border-bottom: 1px solid #334155; }
        th { color: #38bdf8; }
        .status-normal { color: #34d399; font-weight: bold; }
        .status-warn { color: #f43f5e; font-weight: bold; }
    </style>
</head>
<body>
    <div class="header-container">
        <div>
            <h1>🌊 Step 4: Cloud Dataflow & BigQuery Pipeline</h1>
            <p>Event-Time 정렬 및 실시간 데이터 웨어하우스(DW) 적재 시뮬레이터</p>
        </div>
        <a href="/" class="nav-link">👈 1~3단계 관제 대시보드 이동</a>
    </div>

    <div class="grid">
        <div class="card">
            <div class="card-title">수신된 원본 로그 수</div>
            <div class="card-value" id="raw">0</div>
        </div>
        <div class="card">
            <div class="card-title">Dataflow Event-Time 정렬 완료</div>
            <div class="card-value" id="sorted" style="color: #34d399;">0</div>
        </div>
        <div class="card">
            <div class="card-title">지연 도착(Out-of-order) 복구</div>
            <div class="card-value" id="late" style="color: #fbbf24;">0</div>
        </div>
        <div class="card">
            <div class="card-title">BigQuery DW 실시간 적재</div>
            <div class="card-value" id="bq" style="color: #38bdf8;">0</div>
        </div>
    </div>

    <div class="card">
        <div class="card-title" style="margin-bottom: 10px;">🗄️ BigQuery 실시간 시계열 적재 테이블 미리보기</div>
        <div class="table-box">
            <table>
                <thead>
                    <tr>
                        <th>Device ID</th>
                        <th>측정 시간 (Event-Time)</th>
                        <th>진동 수치 (SVM)</th>
                        <th>상태</th>
                        <th>지연 시간 (sec)</th>
                    </tr>
                </thead>
                <tbody id="bqTableBody">
                    <tr><td colspan="5" style="text-align: center; color: #64748b;">데이터 수신 대기 중...</td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <script>
        const ws = new WebSocket(`ws://${location.host}/ws-pipeline`);
        
        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            document.getElementById('raw').innerText = data.raw_incoming;
            document.getElementById('sorted').innerText = data.sorted_processed;
            document.getElementById('late').innerText = data.late_recovered;
            document.getElementById('bq').innerText = data.bq_stored_count;

            const tbody = document.getElementById('bqTableBody');
            if (data.storage.length > 0) {
                tbody.innerHTML = data.storage.slice(-10).reverse().map(row => `
                    <tr>
                        <td>${row.device_id}</td>
                        <td>${row.event_time.split('T')[1].substring(0, 8)}</td>
                        <td>${row.svm}</td>
                        <td class="${row.status === 'WARNING' ? 'status-warn' : 'status-normal'}">${row.status}</td>
                        <td>${row.delay_sec}s</td>
                    </tr>
                `).join('');
            }
        };
    </script>
</body>
</html>
"""

# --- 라우팅 설정 ---
@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    return HTMLResponse(DASHBOARD_HTML)

@app.get("/pipeline", response_class=HTMLResponse)
async def get_pipeline_page():
    return HTMLResponse(PIPELINE_HTML)

@app.post("/reset")
async def reset_statistics():
    global stats, recent_logs, pipeline_stats, bigquery_storage
    stats = {"total_messages": 0, "queue_backlog": 0, "route_a_processed": 0, "route_b_warnings": 0, "late_data": 0, "reconnections": 0}
    pipeline_stats = {"raw_incoming": 0, "sorted_processed": 0, "bq_stored_count": 0, "late_recovered": 0}
    bigquery_storage.clear()
    recent_logs = [f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 모든 통계 및 창고 데이터 초기화 완료"]
    return {"status": "success"}

# --- 웹소켓 엔드포인트들 ---
@app.websocket("/ws-dashboard")
async def dashboard_ws(websocket: WebSocket):
    await websocket.accept()
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

@app.websocket("/ws-pipeline")
async def pipeline_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await asyncio.sleep(0.4)
            payload = {
                "raw_incoming": pipeline_stats["raw_incoming"],
                "sorted_processed": pipeline_stats["sorted_processed"],
                "bq_stored_count": pipeline_stats["bq_stored_count"],
                "late_recovered": pipeline_stats["late_recovered"],
                "storage": bigquery_storage
            }
            await websocket.send_text(json.dumps(payload))
    except WebSocketDisconnect:
        pass

@app.websocket("/ws/{device_id}")
async def sensor_endpoint(websocket: WebSocket, device_id: str):
    await websocket.accept()
    active_connections.add(websocket)
    try:
        while True:
            raw_data = await websocket.receive_text()
            payload = json.JSONDecoder().decode(raw_data) if 'JSONDecoder' in globals() else json.loads(raw_data)
            stats["total_messages"] += 1
            await message_queue.put({"device_id": device_id, "payload": payload})
    except WebSocketDisconnect:
        stats["reconnections"] += 1
    finally:
        active_connections.discard(websocket)

if __name__ == "__main__":
    import uvicorn
    print("🚀 [통합 스마트 팩토리 서버] 실행 중 (포트: 8000)")
    print("   - 1~3단계 관제: http://localhost:8000/")
    print("   - 4단계 파이프라인: http://localhost:8000/pipeline")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")