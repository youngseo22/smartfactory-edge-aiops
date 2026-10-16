import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from shared import pipeline_stats, bigquery_storage

router = APIRouter()

PIPELINE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>스마트 팩토리 - 4단계 파이프라인</title>
    <style>
        body { font-family: -apple-system, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 25px; }
        .header-container { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 15px; }
        h1 { font-size: 24px; margin: 0; color: #10b981; }
        p { color: #94a3b8; margin: 5px 0 0 0; }
        .nav-group { display: flex; gap: 8px; align-items: center; }
        .nav-link { background: #334155; color: white; text-decoration: none; padding: 8px 14px; border-radius: 8px; font-size: 13px; font-weight: bold; transition: background 0.2s; }
        .nav-link:hover { background: #475569; }
        .nav-link.active { background: #059669; }
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
        <div class="nav-group">
            <a href="/" class="nav-link">1~3단계 관제</a>
            <a href="/pipeline" class="nav-link active">4단계 파이프라인</a>
            <a href="/aiops" class="nav-link">5단계 AIOps</a>
        </div>
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

@router.get("/pipeline", response_class=HTMLResponse)
async def get_pipeline_page():
    return HTMLResponse(PIPELINE_HTML)

@router.websocket("/ws-pipeline")
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