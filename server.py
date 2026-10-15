import asyncio
import json
from datetime import datetime, timezone
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI()

# 실시간 통계 및 최근 로그를 담는 전역 변수
active_connections: set[WebSocket] = set()
stats = {"total_messages": 0, "warnings": 0, "late_data": 0, "reconnections": 0}
recent_logs = []

# 📊 웹 관제 대시보드 HTML + JS UI (초기화 버튼 포함)
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>아모레 스마트 팩토리 실시간 관제 대시보드</title>
    <style>
        body { font-family: -apple-system, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 25px; }
        .header-container { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        h1 { font-size: 24px; margin: 0; color: #38bdf8; }
        p { color: #94a3b8; margin: 5px 0 0 0; }
        .reset-btn { background: #f43f5e; color: white; border: none; padding: 10px 20px; font-size: 14px; font-weight: bold; border-radius: 8px; cursor: pointer; transition: background 0.2s; }
        .reset-btn:hover { background: #e11d48; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px; margin-bottom: 25px; }
        .card { background: #1e293b; border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); border: 1px solid #334155; }
        .card-title { font-size: 14px; color: #94a3b8; font-weight: bold; }
        .card-value { font-size: 32px; font-weight: bold; margin-top: 10px; color: #f1f5f9; }
        .warning-val { color: #f43f5e !important; }
        .log-box { background: #1e293b; border-radius: 12px; padding: 20px; border: 1px solid #334155; height: 250px; overflow-y: auto; font-family: monospace; font-size: 13px; }
        .log-item { margin-bottom: 8px; border-bottom: 1px solid #334155; padding-bottom: 4px; }
        .log-warn { color: #f43f5e; font-weight: bold; }
    </style>
</head>
<body>
    <div class="header-container">
        <div>
            <h1>🏭 Smart Factory AIOps Control Center</h1>
            <p>GKE WebSocket Gateway & Cloud-Native Stream Monitoring</p>
        </div>
        <button class="reset-btn" onclick="resetStats()">🔄 통계 초기화 (Reset)</button>
    </div>

    <div class="grid">
        <div class="card">
            <div class="card-title">활성 WebSocket 연결</div>
            <div class="card-value" id="conns">0</div>
        </div>
        <div class="card">
            <div class="card-title">누적 수신 메시지</div>
            <div class="card-value" id="total">0</div>
        </div>
        <div class="card">
            <div class="card-title">지연 도착 (Out-of-order)</div>
            <div class="card-value" id="lates">0</div>
        </div>
        <div class="card">
            <div class="card-title">🚨 이상 진동 (WARNING)</div>
            <div class="card-value warning-val" id="warnings">0</div>
        </div>
    </div>

    <div class="card">
        <div class="card-title" style="margin-bottom: 10px;">실시간 이벤트 및 장애 로그 브리프</div>
        <div class="log-box" id="logBox">
            <div class="log-item">시스템 대시보드 연결 완료. 테스트를 시작하세요.</div>
        </div>
    </div>

    <script>
        const ws = new WebSocket(`ws://${location.host}/ws-dashboard`);
        
        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            document.getElementById('conns').innerText = data.connections;
            document.getElementById('total').innerText = data.total_messages;
            document.getElementById('lates').innerText = data.late_data;
            document.getElementById('warnings').innerText = data.warnings;

            const logBox = document.getElementById('logBox');
            logBox.innerHTML = data.logs.map(log => 
                `<div class="log-item ${log.includes('긴급') || log.includes('이상') ? 'log-warn' : ''}">${log}</div>`
            ).join('');
            logBox.scrollTop = logBox.scrollHeight;
        };

        function resetStats() {
            fetch('/reset', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    console.log("Stats reset:", data);
                });
        }
    </script>
</body>
</html>
"""

@app.get("/")
async def get_dashboard():
    return HTMLResponse(DASHBOARD_HTML)

# 🔄 통계 초기화 API 엔드포인트
@app.post("/reset")
async def reset_statistics():
    global stats, recent_logs
    stats = {"total_messages": 0, "warnings": 0, "late_data": 0, "reconnections": 0}
    recent_logs = [f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 사용자에 의해 통계 데이터가 초기화되었습니다."]
    return {"status": "success"}

dashboard_clients: set[WebSocket] = set()

@app.websocket("/ws-dashboard")
async def dashboard_ws(websocket: WebSocket):
    await websocket.accept()
    dashboard_clients.add(websocket)
    try:
        while True:
            await asyncio.sleep(0.5)
            payload = {
                "connections": len(active_connections),
                "total_messages": stats["total_messages"],
                "late_data": stats["late_data"],
                "warnings": stats["warnings"],
                "logs": recent_logs[-15:]
            }
            await websocket.send_text(json.dumps(payload))
    except WebSocketDisconnect:
        pass
    finally:
        dashboard_clients.discard(websocket)

def add_log(msg: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    recent_logs.append(f"[{timestamp}] {msg}")

@app.websocket("/ws/{device_id}")
async def sensor_endpoint(websocket: WebSocket, device_id: str):
    await websocket.accept()
    active_connections.add(websocket)
    try:
        while True:
            raw_data = await websocket.receive_text()
            payload = json.loads(raw_data)
            stats["total_messages"] += 1

            server_time = datetime.now(timezone.utc)
            try:
                event_time = datetime.fromisoformat(payload["event_time"].replace("Z", "+00:00"))
                delay_sec = (server_time.replace(tzinfo=None) - event_time.replace(tzinfo=None)).total_seconds()
            except Exception:
                delay_sec = 0.0

            if delay_sec > 1.5:
                stats["late_data"] += 1

            if payload.get("status") == "WARNING":
                stats["warnings"] += 1
                log_msg = f"🚨 [이상 감지] 기기: {device_id} | SVM: {payload['svm']}"
                add_log(log_msg)

    except WebSocketDisconnect:
        stats["reconnections"] += 1
    finally:
        active_connections.discard(websocket)

if __name__ == "__main__":
    import uvicorn
    print("🚀 스마트 팩토리 실시간 관제 대시보드 서버 시작 (포트: 8000)")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")