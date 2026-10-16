import asyncio
import json
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from shared import message_queue, active_connections, stats, pipeline_stats, bigquery_storage, add_log
from routes_dashboard import router as dashboard_router
from routes_pipeline import router as pipeline_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    async def background_unified_worker():
        while True:
            item = await message_queue.get()
            payload = item["payload"]
            device_id = item["device_id"]
            
            server_time = datetime.now(timezone.utc)
            try:
                event_time = datetime.fromisoformat(payload["event_time"].replace("Z", "+00:00"))
                delay_sec = (server_time.replace(tzinfo=None) - event_time.replace(tzinfo=None)).total_seconds()
            except Exception:
                delay_sec = 0.0

            # 1~3단계 로직 처리
            stats["queue_backlog"] = message_queue.qsize()
            if delay_sec > 1.5:
                stats["late_data"] += 1
            stats["route_a_processed"] += 1

            if payload.get("status") == "WARNING":
                stats["route_b_warnings"] += 1
                add_log(f"🚨 [Route B 긴급] AI Agent 호출 | 기기: {device_id} | SVM: {payload['svm']}")

            # 4단계 파이프라인 로직 처리
            pipeline_stats["raw_incoming"] += 1
            if delay_sec > 1.0:
                pipeline_stats["late_recovered"] += 1
            pipeline_stats["sorted_processed"] += 1
            pipeline_stats["bq_stored_count"] += 1
            
            bigquery_storage.append({
                "device_id": device_id,
                "event_time": payload["event_time"],
                "svm": payload["svm"],
                "status": payload["status"],
                "delay_sec": round(delay_sec, 2)
            })
            if len(bigquery_storage) > 50:
                bigquery_storage.pop(0)

            message_queue.task_done()

    asyncio.create_task(background_unified_worker())
    yield

app = FastAPI(lifespan=lifespan)

# 라우터 등록
app.include_router(dashboard_router)
app.include_router(pipeline_router)

# 센서 데이터 수신 웹소켓 엔드포인트
@app.websocket("/ws/{device_id}")
async def sensor_endpoint(websocket: WebSocket, device_id: str):
    await websocket.accept()
    active_connections.add(websocket)
    try:
        while True:
            raw_data = await websocket.receive_text()
            payload = json.loads(raw_data)
            stats["total_messages"] += 1
            await message_queue.put({"device_id": device_id, "payload": payload})
    except WebSocketDisconnect:
        stats["reconnections"] += 1
    finally:
        active_connections.discard(websocket)

if __name__ == "__main__":
    import uvicorn
    print("🚀 [모듈러 통합 서버] 실행 중 (포트: 8000)")
    print("   - 1~3단계 관제: http://localhost:8000/")
    print("   - 4단계 파이프라인: http://localhost:8000/pipeline")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")