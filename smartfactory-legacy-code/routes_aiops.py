import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from shared import aiops_logs, aiops_stats

router = APIRouter()

AIOPS_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>스마트 팩토리 - 5단계 AIOps 에이전트</title>
    <style>
        body { font-family: -apple-system, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 25px; }
        .header-container { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 15px; }
        h1 { font-size: 24px; margin: 0; color: #a855f7; }
        p { color: #94a3b8; margin: 5px 0 0 0; }
        .nav-group { display: flex; gap: 8px; align-items: center; }
        .nav-link { background: #334155; color: white; text-decoration: none; padding: 8px 14px; border-radius: 8px; font-size: 13px; font-weight: bold; transition: background 0.2s; }
        .nav-link:hover { background: #475569; }
        .nav-link.active { background: #7e22ce; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px; margin-bottom: 25px; }
        .card { background: #1e293b; border-radius: 12px; padding: 18px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); border: 1px solid #334155; }
        .card-title { font-size: 13px; color: #94a3b8; font-weight: bold; }
        .card-value { font-size: 28px; font-weight: bold; margin-top: 8px; color: #f1f5f9; }
        .ai-box { background: #1e293b; border-radius: 12px; padding: 20px; border: 1px solid #a855f7; height: 280px; overflow-y: auto; font-family: monospace; font-size: 13px; }
        .ai-item { margin-bottom: 12px; border-bottom: 1px solid #334155; padding-bottom: 8px; }
        .ai-title { color: #c084fc; font-weight: bold; }
        .ai-desc { color: #e2e8f0; margin-top: 4px; }
    </style>
</head>
<body>
    <div class="header-container">
        <div>
            <h1>🤖 Step 5: Vertex AI RAG Agent & Slack Alerting</h1>
            <p>설비 이상 징후 자동 진단, 사내 매뉴얼 검색(RAG) 및 슬랙 긴급 대응 브리핑</p>
        </div>
        <div class="nav-group">
            <a href="/" class="nav-link">1~3단계 관제</a>
            <a href="/pipeline" class="nav-link">4단계 파이프라인</a>
            <a href="/aiops" class="nav-link active">5단계 AIOps</a>
        </div>
    </div>

    <div class="grid">
        <div class="card">
            <div class="card-title">AI 에이전트 분석 총 건수</div>
            <div class="card-value" id="aiTotal">0</div>
        </div>
        <div class="card">
            <div class="card-title">RAG 매뉴얼 검색 횟수</div>
            <div class="card-value" id="ragCount" style="color: #c084fc;">0</div>
        </div>
        <div class="card">
            <div class="card-title">Slack 긴급 알림 전송</div>
            <div class="card-value" id="slackCount" style="color: #f43f5e;">0</div>
        </div>
    </div>

    <div class="card">
        <div class="card-title" style="margin-bottom: 10px;">🧠 Vertex AI RAG 기반 실시간 장애 진단 및 가이드 브리프</div>
        <div class="ai-box" id="aiBox">
            <div class="ai-item">시스템 대기 중... 이상 징후 감지 시 AI 에이전트가 가이드를 생성합니다.</div>
        </div>
    </div>

    <script>
        const ws = new WebSocket(`ws://${location.host}/ws-aiops`);
        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            document.getElementById('aiTotal').innerText = data.ai_total;
            document.getElementById('ragCount').innerText = data.rag_count;
            document.getElementById('slackCount').innerText = data.slack_count;

            const aiBox = document.getElementById('aiBox');
            aiBox.innerHTML = data.logs.map(log => `
                <div class="ai-item">
                    <div class="ai-title">${log.time} | [${log.device_id}] 이상 진동 (SVM: ${log.svm})</div>
                    <div class="ai-desc">💡 <b>AI 진단:</b> ${log.diagnosis}</div>
                    <div class="ai-desc" style="color: #38bdf8;">📖 <b>매뉴얼 참조(RAG):</b> ${log.manual_ref}</div>
                </div>
            `).join('');
            aiBox.scrollTop = aiBox.scrollHeight;
        };
    </script>
</body>
</html>
"""

@router.get("/aiops", response_class=HTMLResponse)
async def get_aiops_page():
    return HTMLResponse(AIOPS_HTML)

@router.websocket("/ws-aiops")
async def aiops_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await asyncio.sleep(0.4)
            payload = {
                "ai_total": aiops_stats["ai_total"],
                "rag_count": aiops_stats["rag_count"],
                "slack_count": aiops_stats["slack_count"],
                "logs": aiops_logs[-10:]
            }
            await websocket.send_text(json.dumps(payload))
    except WebSocketDisconnect:
        pass