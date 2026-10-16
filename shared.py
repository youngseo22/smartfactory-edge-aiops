import asyncio

# 공용 메시지 큐 (Pub/Sub 역할)
message_queue = asyncio.Queue()

# 활성 웹소켓 연결 목록
active_connections = set()

# 1~3단계 통계 데이터
stats = {
    "total_messages": 0,
    "queue_backlog": 0,
    "route_a_processed": 0,
    "route_b_warnings": 0,
    "late_data": 0,
    "reconnections": 0
}
recent_logs = []

# 4단계 파이프라인 통계 데이터
pipeline_stats = {
    "raw_incoming": 0,
    "sorted_processed": 0,
    "bq_stored_count": 0,
    "late_recovered": 0
}
bigquery_storage = []

def add_log(msg: str):
    from datetime import datetime
    timestamp = datetime.now().strftime("%H:%M:%S")
    recent_logs.append(f"[{timestamp}] {msg}")
    if len(recent_logs) > 20:
        recent_logs.pop(0)