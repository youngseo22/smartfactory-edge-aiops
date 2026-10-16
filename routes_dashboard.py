import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from shared import stats, recent_logs, active_connections, message_queue

router = APIRouter()

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
        .reset-btn { background: #f43f5e; color: white; border: none; padding: 10px 20px; font-size: 14px; font-weight: bold; border-radius: 8px; cursor: pointer; }
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

@router.get("/", response_class=HTMLResponse)
async def get_dashboard():
    return HTMLResponse(DASHBOARD_HTML)

@router.post("/reset")
async def reset_statistics():
    global stats, recent_logs
    stats.update({"total_messages": 0, "queue_backlog": 0, "route_a_processed": 0, "route_b_warnings": 0, "late_data": 0, "reconnections": 0})
    recent_logs.clear()
    return {"status": "success"}

@router.websocket("/ws-dashboard")
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