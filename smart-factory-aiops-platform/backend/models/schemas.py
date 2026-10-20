"""Step 1 — 센서 데이터 / 시계열 히스토리 / 컨테이너(Pod) 상태 Pydantic 모델."""
from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from typing import Deque, Generic, Iterator, Literal, Optional, TypeVar

from pydantic import BaseModel, Field, model_validator

T = TypeVar("T")

Domain = Literal["FACTORY", "FULFILLMENT", "ORDER"]
AlertType = Literal["VIBRATION_HIGH", "CONVEYOR_ANOMALY", "BACKLOG_HIGH", "NODE_DOWN", "TEMP_HIGH"]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def epoch_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


# ─────────────────────────────────────────────────────────────
# Stage 1: Edge 센서 페이로드
# ─────────────────────────────────────────────────────────────
class MotorMetrics(BaseModel):
    """COSMETIC_MOTOR — 화장품 캡 조립 모터"""
    vibration_svm: float
    torque_nm: float
    rpm: float


class ColdChainMetrics(BaseModel):
    """COLDCHAIN_ENV — 콜드체인 온·습도"""
    temperature_c: float
    humidity_pct: float


class SensorReading(BaseModel):
    """Gateway가 수신하는 공통 센서 메시지 (plan.md §4 Stage 1 JSON 규격)."""
    sensor_id: str
    domain: Domain
    timestamp: str = Field(default_factory=utc_now_iso)
    metrics: dict[str, float]
    node_zone: Optional[str] = None
    status: Optional[str] = None
    heartbeat: Optional[bool] = None
    seq: Optional[int] = None  # 콜드체인 논리 시퀀스 (데이터 유실 0% 검증용)

    @model_validator(mode="after")
    def _check_metrics(self) -> "SensorReading":
        if self.domain == "FACTORY":
            MotorMetrics.model_validate(self.metrics)
        elif self.domain == "FULFILLMENT":
            ColdChainMetrics.model_validate(self.metrics)
        return self

    @property
    def event_epoch(self) -> float:
        return datetime.fromisoformat(self.timestamp.replace("Z", "+00:00")).timestamp()


class AlertEvent(BaseModel):
    """Route B(이상 징후) 메시지 — Stage 5 AIOps Engine 입력."""
    type: AlertType
    source: str
    zone: Optional[str] = None
    value: Optional[float] = None
    threshold: Optional[float] = None
    ts: float = Field(default_factory=lambda: datetime.now(timezone.utc).timestamp())


# ─────────────────────────────────────────────────────────────
# 시계열 버퍼 (최근 N개 포인트 슬라이딩 윈도우)
# ─────────────────────────────────────────────────────────────
class RollingBuffer(Generic[T]):
    def __init__(self, maxlen: int = 30) -> None:
        self._d: Deque[T] = deque(maxlen=maxlen)

    def append(self, item: T) -> None:
        self._d.append(item)

    def clear(self) -> None:
        self._d.clear()

    def last(self) -> Optional[T]:
        return self._d[-1] if self._d else None

    def to_list(self) -> list[T]:
        return list(self._d)

    def __len__(self) -> int:
        return len(self._d)

    def __iter__(self) -> Iterator[T]:
        return iter(self._d)


class TempPoint(BaseModel):
    """temp_history 1 포인트. Zone A는 temp_a, Zone B는 temp_b 시리즈로 기록."""
    ts: int
    temp_a: Optional[float] = None
    temp_b: Optional[float] = None
    zone: str = "ZONE_A"


class SvmPoint(BaseModel):
    ts: int
    svm: float


# ─────────────────────────────────────────────────────────────
# 대시보드 스냅샷 구성 요소
# ─────────────────────────────────────────────────────────────
class PodState(BaseModel):
    id: int
    status: Literal["ACTIVE", "STARTING", "TERMINATING", "STANDBY"] = "STANDBY"
    load_pct: int = 0


class MotorState(BaseModel):
    sensor_id: str = "MOTOR_LINE_A_01"
    svm: float = 0.0
    torque_nm: float = 0.0
    rpm: float = 0.0
    status: Literal["NORMAL", "WARNING", "OFFLINE"] = "NORMAL"


class ZoneState(BaseModel):
    zone: str
    role: Literal["PRIMARY", "BACKUP"]
    status: Literal["ONLINE", "WARNING", "OFFLINE", "UNKNOWN"] = "UNKNOWN"
    serving: bool = False
    temp_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    last_seen_age_s: Optional[float] = None


class RoutingState(BaseModel):
    primary_zone: str = "ZONE_A"
    backup_zone: str = "ZONE_B"
    active_zone: str = "ZONE_A"
    failover_active: bool = False
    data_loss_pct: float = 0.0
    replayed: int = 0
    switched_at: Optional[int] = None
    table: dict[str, str] = Field(default_factory=lambda: {"ZONE_A": "ZONE_A", "ZONE_B": "ZONE_B"})


class QueueState(BaseModel):
    backlog_count: int = 0
    bottleneck_pct: float = 0.0           # backlog / 임계치(1,000) × 100
    severity: Literal["OK", "WARN", "CRIT"] = "OK"
    throughput_pct: int = 100             # 활성 워커 수 / 기본 워커 수 × 100
    rows_written: int = 0


class PipelineRates(BaseModel):
    edge_rate: float = 0.0     # Edge → Gateway (msg/s)
    route_a_rate: float = 0.0  # Gateway → Pub/Sub
    route_b_rate: float = 0.0  # 이상 징후 → AIOps
    drain_rate: float = 0.0    # 워커 소비량
    bq_rate: float = 0.0       # BigQuery 적재량


# ── 자율 대응 액션 상태 ─────────────────────────────────────
class SlackCard(BaseModel):
    channel: str = "#aiops-factory"
    severity: Literal["WARN", "CRIT"] = "CRIT"
    manual_page: int
    manual_title: str
    key_action: str
    cause: str
    confidence: float
    svm: float
    ts: int


class ScaleAction(BaseModel):
    from_pods: int
    to_pods: int
    status: Literal["RUNNING", "DONE"] = "RUNNING"
    ts: int


class FailoverAction(BaseModel):
    from_zone: str
    to_zone: str
    status: Literal["DONE", "NO_BACKUP"] = "DONE"
    data_loss_pct: float = 0.0
    replayed: int = 0
    ts: int


class RemediationState(BaseModel):
    slack: Optional[SlackCard] = None       # Action A: SLACK_ALERT
    scale: Optional[ScaleAction] = None     # Action B: CONTAINER_SCALE_UP
    failover: Optional[FailoverAction] = None  # Action C: NODE_FAILOVER


class DashboardSnapshot(BaseModel):
    """/ws/dashboard 로 0.5초마다 전송되는 전체 상태."""
    ts: int
    mode: str
    active_scenarios: list[int]
    motor: MotorState
    svm_history: list[SvmPoint]
    temp_history: list[TempPoint]
    zones: dict[str, ZoneState]
    routing: RoutingState
    queue: QueueState
    pipeline: PipelineRates
    worker_pods: list[PodState]
    remediation: RemediationState
    events: list[str]  # 최근 5초 내 발생한 이벤트 코드 (아이콘 점멸용)
