"""Pydantic 데이터 모델.

- Stage 1 센서 페이로드 (COSMETIC_MOTOR / COLDCHAIN_ENV / ORDER)
- 실시간 차트용 시계열 히스토리 (temp_history, svm_history: 최근 30 포인트)
- 6개 워커 컨테이너 개별 상태 (worker_pods)
- 대시보드 WebSocket 스냅샷
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal, Optional, Union

from pydantic import BaseModel, Field, TypeAdapter


# ════════════════════════════════════════════════════════════════
# Enums
# ════════════════════════════════════════════════════════════════
class ScenarioId(str, Enum):
    NORMAL = "NORMAL"
    SCENARIO_1 = "SCENARIO_1"
    SCENARIO_2 = "SCENARIO_2"


class SensorStatus(str, Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class PodState(str, Enum):
    STANDBY = "STANDBY"
    BOOTING = "BOOTING"
    ACTIVE = "ACTIVE"
    DRAINING = "DRAINING"


class ZoneStatus(str, Enum):
    ONLINE = "ONLINE"
    WARNING = "WARNING"
    OFFLINE = "OFFLINE"
    STANDBY = "STANDBY"
    BACKUP_ON = "BACKUP_ON"


class EventType(str, Enum):
    VIBRATION_ANOMALY = "VIBRATION_ANOMALY"
    BACKLOG_HIGH = "BACKLOG_HIGH"
    NODE_DOWN = "NODE_DOWN"
    TEMP_HIGH = "TEMP_HIGH"


class ActionType(str, Enum):
    SLACK_ALERT = "SLACK_ALERT"
    CONTAINER_SCALE_UP = "CONTAINER_SCALE_UP"
    CONTAINER_SCALE_DOWN = "CONTAINER_SCALE_DOWN"
    NODE_FAILOVER = "NODE_FAILOVER"
    DIAGNOSIS = "DIAGNOSIS"


# ════════════════════════════════════════════════════════════════
# Stage 1 · Edge sensor payloads
# ════════════════════════════════════════════════════════════════
class MotorMetrics(BaseModel):
    vibration_svm: float
    torque_nm: float
    rpm: int


class CosmeticMotorPayload(BaseModel):
    """화장품 캡 조립 모터 센서 (COSMETIC_MOTOR)."""

    sensor_id: str = "MOTOR_LINE_A_01"
    domain: Literal["FACTORY"] = "FACTORY"
    timestamp: datetime
    metrics: MotorMetrics
    status: SensorStatus = SensorStatus.NORMAL
    seq: int = 0


class ColdChainMetrics(BaseModel):
    temperature_c: float
    humidity_pct: float


class ColdChainPayload(BaseModel):
    """물류 창고 콜드체인 온·습도 센서 (COLDCHAIN_ENV)."""

    sensor_id: str = "COLD_ZONE_A_01"
    node_zone: str = "ZONE_A"
    domain: Literal["FULFILLMENT"] = "FULFILLMENT"
    timestamp: datetime
    metrics: ColdChainMetrics
    heartbeat: bool = True
    seq: int = 0
    routed_via: Optional[str] = None
    replayed: bool = False


class OrderEvent(BaseModel):
    """마감 세일 주문 트래픽 (큐 적체 시뮬레이션 용)."""

    order_id: str
    domain: Literal["ORDER"] = "ORDER"
    timestamp: datetime
    sku: str
    qty: int = 1
    seq: int = 0


SensorPayload = Annotated[
    Union[CosmeticMotorPayload, ColdChainPayload, OrderEvent],
    Field(discriminator="domain"),
]
ingest_adapter: TypeAdapter[SensorPayload] = TypeAdapter(SensorPayload)


# ════════════════════════════════════════════════════════════════
# Pipeline events (Route B → Stage 5)
# ════════════════════════════════════════════════════════════════
class PipelineEvent(BaseModel):
    event_type: EventType
    source: str
    severity: SensorStatus = SensorStatus.WARNING
    ts: float
    payload: dict[str, Any] = Field(default_factory=dict)


# ════════════════════════════════════════════════════════════════
# Time-series points (차트 좌표)
# ════════════════════════════════════════════════════════════════
class TempPoint(BaseModel):
    t: float                                   # bucket epoch seconds
    zone_a: Optional[float] = None             # ZONE_A 센서 온도
    zone_b: Optional[float] = None             # ZONE_B 센서 온도
    route: Optional[Literal["ZONE_A", "ZONE_B"]] = None  # ZONE_A 데이터 수집 경로
    a_primary: Optional[float] = None          # ZONE_A 센서값 (Primary 수집 경로)
    a_backup: Optional[float] = None           # ZONE_A 센서값 (ZONE_B 우회 경로)


class SvmPoint(BaseModel):
    t: float
    svm: Optional[float] = None
    torque: Optional[float] = None
    rpm: Optional[int] = None


# ════════════════════════════════════════════════════════════════
# Dashboard state blocks
# ════════════════════════════════════════════════════════════════
class WorkerPod(BaseModel):
    pod_id: str
    index: int
    state: PodState
    load_pct: float = 0.0
    processed: int = 0
    boosted: bool = False                      # Scale-up 으로 추가된 Pod 여부


class PipelineStats(BaseModel):
    edge_rate: float
    ingress_rate: float
    route_a_rate: float
    route_b_rate: float
    consume_rate: float
    backlog_count: int
    backlog_threshold: int
    bottleneck_pct: float
    bq_rows: int
    ai_events: int


class MotorState(BaseModel):
    sensor_id: str
    vibration_svm: float
    torque_nm: float
    rpm: int
    status: SensorStatus
    threshold: float
    critical: float


class FactoryState(BaseModel):
    motor: MotorState
    svm_history: list[SvmPoint]
    worker_pods: list[WorkerPod]
    active_workers: int
    base_workers: int
    max_workers: int
    throughput_pct: float


class ZoneState(BaseModel):
    zone: str
    role: Literal["PRIMARY", "BACKUP"]
    status: ZoneStatus
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    last_seen_ago_s: float
    link_up: bool


class ColdChainState(BaseModel):
    temp_history: list[TempPoint]
    zones: dict[str, ZoneState]
    temp_threshold: float


class RoutingState(BaseModel):
    table: dict[str, str]
    failover_active: bool
    data_loss_pct: float
    buffered_msgs: int
    recovered_msgs: int


class SlackCard(BaseModel):
    active: bool = False
    page: Optional[str] = None
    title: Optional[str] = None
    keyword: Optional[str] = None
    metric: Optional[str] = None
    severity: SensorStatus = SensorStatus.WARNING
    source: Literal["LOCAL_RAG", "VERTEX_AI"] = "LOCAL_RAG"
    confidence: float = 0.0
    delivered: bool = False
    ts: Optional[float] = None


class ScaleUpWidget(BaseModel):
    active: bool = False
    from_pods: int = 2
    to_pods: int = 2
    active_pods: int = 2
    throughput_pct: float = 100.0
    ts: Optional[float] = None


class FailoverWidget(BaseModel):
    active: bool = False
    from_zone: str = "ZONE_A"
    to_zone: str = "ZONE_B"
    data_loss_pct: float = 0.0
    recovered_msgs: int = 0
    ts: Optional[float] = None


class RemediationState(BaseModel):
    slack: SlackCard
    scale_up: ScaleUpWidget
    failover: FailoverWidget


class ActionRecord(BaseModel):
    action: ActionType
    target: str
    ts: float
    meta: dict[str, Any] = Field(default_factory=dict)


class DashboardSnapshot(BaseModel):
    ts: float
    scenario: ScenarioId
    mode: Literal["MOCK", "GCP"]
    pipeline: PipelineStats
    factory: FactoryState
    coldchain: ColdChainState
    routing: RoutingState
    remediation: RemediationState
    actions: list[ActionRecord]
