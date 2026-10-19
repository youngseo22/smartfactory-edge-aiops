"""환경 변수 및 임계치(Threshold) 설정.

로컬 시연(Mock) 모드가 기본이며, `USE_GCP=true` 로 설정하면
Pub/Sub · BigQuery · Vertex AI 실제 연동 어댑터를 사용하도록 추상화되어 있다.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    # ── Runtime mode ───────────────────────────────────────────────
    use_gcp: bool = _env_bool("USE_GCP", False)
    gcp_project: str = os.getenv("GCP_PROJECT", "")
    gcp_location: str = os.getenv("GCP_LOCATION", "asia-northeast3")
    pubsub_topic_raw: str = os.getenv("PUBSUB_TOPIC_RAW", "iot-raw-route-a")
    pubsub_topic_anomaly: str = os.getenv("PUBSUB_TOPIC_ANOMALY", "iot-anomaly-route-b")
    bq_table: str = os.getenv("BQ_TABLE", "aiops.iot_raw_logs")
    vertex_model: str = os.getenv("VERTEX_MODEL", "gemini-1.5-flash")
    slack_webhook_url: str = os.getenv("SLACK_WEBHOOK_URL", "")
    cors_origins: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()
        )
    )

    # ── Thresholds ────────────────────────────────────────────────
    vibration_threshold: float = _env_float("VIBRATION_THRESHOLD", 7.0)
    vibration_critical: float = _env_float("VIBRATION_CRITICAL", 10.0)
    backlog_threshold: int = _env_int("BACKLOG_THRESHOLD", 1000)
    temp_threshold_c: float = _env_float("TEMP_THRESHOLD_C", 8.0)
    heartbeat_timeout_s: float = _env_float("HEARTBEAT_TIMEOUT_S", 3.0)

    # ── Dataflow worker pool (Stage 4) ────────────────────────────
    base_workers: int = 2
    max_workers: int = 6
    worker_batch_size: int = 20          # 워커 1개가 tick 당 처리하는 메시지 수
    worker_tick_s: float = 0.5           # → 워커 1개당 40 msg/s
    pod_boot_stagger_s: float = 0.45     # 컨테이너 순차 점등 간격

    # ── Edge simulator (Stage 1) ──────────────────────────────────
    edge_tick_s: float = 0.25            # 센서 4 Hz
    base_order_rate: float = 20.0        # 평상시 주문 이벤트 msg/s
    surge_burst_orders: int = 1150       # 마감 세일 순간 폭주량
    surge_burst_s: float = 1.5
    surge_order_rate: float = 110.0      # 폭주 이후 지속 유입량 msg/s
    surge_duration_s: float = 25.0
    s2_temp_ramp_s: float = 4.0          # 시나리오2 온도 상승 시간
    s2_link_fault_after_s: float = 4.0   # 시나리오2 네트워크 단절 시점

    # ── AIOps / Dashboard ─────────────────────────────────────────
    ai_diagnosis_delay_s: float = 0.6
    broadcast_interval_s: float = 0.5
    history_points: int = 30
    history_bucket_s: float = 1.0


settings = Settings()
