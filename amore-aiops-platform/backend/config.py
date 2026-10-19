"""환경 변수 및 임계치(Threshold) 설정.

AIOPS_MODE=mock (기본) : 인메모리 큐 + SQLite + 로컬 RAG + Mock Slack  → 로컬에서 즉시 시연 가능
AIOPS_MODE=gcp         : Cloud Pub/Sub + BigQuery + Vertex AI(Gemini) RAG + Slack Webhook
"""
from __future__ import annotations

import os
from dataclasses import dataclass


from pathlib import Path

# .env 파일 자동 로딩 (python-dotenv가 있으면 사용, 없으면 내장 경량 파서로 로드)
def _load_dotenv_if_exists() -> None:
    try:
        from dotenv import load_dotenv  # type: ignore
        for env_path in [Path(__file__).parent / ".env", Path(__file__).resolve().parents[1] / ".env"]:
            if env_path.is_file():
                load_dotenv(dotenv_path=env_path)
    except ImportError:
        # 경량 fallback 파서
        for env_path in [Path(__file__).parent / ".env", Path(__file__).resolve().parents[1] / ".env"]:
            if env_path.is_file():
                try:
                    for line in env_path.read_text(encoding="utf-8").splitlines():
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k, v = k.strip(), v.strip().strip("'\"")
                            if k and k not in os.environ:
                                os.environ[k] = v
                except Exception:
                    pass

_load_dotenv_if_exists()

# GOOGLE_APPLICATION_CREDENTIALS 설정 (프로젝트 루트의 gcp-key.json 최우선 적용)
_root_dir = Path(__file__).resolve().parents[1]
_local_key = _root_dir / "gcp-key.json"
if _local_key.is_file():
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(_local_key.resolve())
else:
    _cred_env = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if _cred_env:
        _cred_path = Path(_cred_env)
        if not _cred_path.is_absolute():
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str((_root_dir / _cred_path).resolve())


def _f(name: str, default: float) -> float:
    val = os.getenv(name)
    if val is None or not str(val).strip():
        return default
    try:
        return float(val)
    except ValueError:
        return default


def _i(name: str, default: int) -> int:
    val = os.getenv(name)
    if val is None or not str(val).strip():
        return default
    try:
        return int(val)
    except ValueError:
        return default


def _s(name: str, default: str) -> str:
    val = os.getenv(name)
    if val is None or not str(val).strip():
        return default
    return str(val).strip()



@dataclass(frozen=True)
class Settings:
    # ── 실행 모드 ────────────────────────────────────────────────
    mode: str = _s("AIOPS_MODE", "mock").lower()          # mock | gcp
    edge_transport: str = _s("EDGE_TRANSPORT", "inproc")   # inproc | ws
    ingest_ws_url: str = _s("INGEST_WS_URL", "ws://127.0.0.1:8000/ws/ingest")

    # ── 임계치 (plan.md §4 Stage 3) ──────────────────────────────
    svm_threshold: float = _f("SVM_THRESHOLD", 7.0)
    backlog_threshold: int = _i("BACKLOG_THRESHOLD", 1000)
    temp_threshold_c: float = _f("TEMP_THRESHOLD_C", 8.0)
    heartbeat_timeout_s: float = _f("HEARTBEAT_TIMEOUT_S", 2.0)

    # ── 시뮬레이션 파라미터 ──────────────────────────────────────
    svm_normal: float = 2.8
    svm_fault: float = 8.5            # 시나리오 1: 진동 수치
    burst_total: int = _i("BURST_TOTAL", 1250)  # 시나리오 1: 주문 폭주 (피크 ≈ 1,200건)
    burst_chunks: int = 25
    heat_ticks_before_cut: int = 5    # 시나리오 2: 온도 상승 후 노드 단절까지 틱 수
    motor_period_s: float = 0.5
    cold_period_s: float = 1.0

    # ── Stage 4 워커 풀 ──────────────────────────────────────────
    base_workers: int = 2
    max_workers: int = 6
    worker_tick_s: float = 0.1
    worker_batch: int = 4             # 워커 1개 = 40 msg/s
    worker_start_stagger_s: float = 0.35
    window_s: float = 1.0
    allowed_lateness_s: float = 2.0
    auto_scale_down_after_s: float = _f("AUTO_SCALE_DOWN_AFTER_S", 5.0)  # 0 = 비활성, 큐 해소 5초 후 정상 복귀

    # ── 대시보드 ────────────────────────────────────────────────
    broadcast_interval_s: float = 0.5
    history_points: int = 30

    # ── GCP / 외부 연동 (mode=gcp 일 때만 사용) ──────────────────
    gcp_project: str = _s("GCP_PROJECT", "")
    pubsub_raw_topic: str = _s("PUBSUB_RAW_TOPIC", "iot-raw-logs")
    pubsub_raw_sub: str = _s("PUBSUB_RAW_SUB", "iot-raw-logs-sub")
    pubsub_alert_topic: str = _s("PUBSUB_ALERT_TOPIC", "iot-anomalies")
    pubsub_alert_sub: str = _s("PUBSUB_ALERT_SUB", "iot-anomalies-sub")
    bq_dataset: str = _s("BQ_DATASET", "aiops")
    bq_table: str = _s("BQ_TABLE", "iot_raw_logs")
    vertex_location: str = _s("VERTEX_LOCATION", "asia-northeast3")
    vertex_model: str = _s("VERTEX_MODEL", "gemini-2.5-flash")
    slack_webhook_url: str = _s("SLACK_WEBHOOK_URL", "")

    @property
    def use_gcp(self) -> bool:
        return self.mode == "gcp"


settings = Settings()

# 브로커 토픽 이름 (Route A: 전체 로그 / Route B: 이상 징후)
TOPIC_RAW = "iot-raw-logs"
TOPIC_ALERT = "iot-anomalies"
