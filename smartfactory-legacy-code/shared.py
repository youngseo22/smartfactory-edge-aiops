import asyncio

message_queue = asyncio.Queue()
active_connections = set()

stats = {
    "total_messages": 0, "queue_backlog": 0,
    "route_a_processed": 0, "route_b_warnings": 0,
    "late_data": 0, "reconnections": 0
}
recent_logs = []

pipeline_stats = {
    "raw_incoming": 0, "sorted_processed": 0,
    "bq_stored_count": 0, "late_recovered": 0
}
bigquery_storage = []

# 5단계 AIOps 전용 저장소
aiops_stats = {
    "ai_total": 0,
    "rag_count": 0,
    "slack_count": 0
}
aiops_logs = []

def add_log(msg: str):
    from datetime import datetime
    timestamp = datetime.now().strftime("%H:%M:%S")
    recent_logs.append(f"[{timestamp}] {msg}")
    if len(recent_logs) > 20:
        recent_logs.pop(0)

def add_aiops_log(device_id: str, svm: float):
    from datetime import datetime
    aiops_stats["ai_total"] += 1
    aiops_stats["rag_count"] += 1
    aiops_stats["slack_count"] += 1
    
    aiops_logs.append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "device_id": device_id,
        "svm": svm,
        "diagnosis": "모터 베어링 마모 및 축 정렬 불량 의심 (임계치 초과)",
        "manual_ref": "Amore_Factory_Maintenance_Manual_v2.pdf (p.42 - 진동 조치 가이드)"
    })
    if len(aiops_logs) > 15:
        aiops_logs.pop(0)