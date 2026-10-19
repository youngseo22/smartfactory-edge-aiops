"""공유 런타임 상태 저장소 — 파이프라인 각 단계가 쓰고, /ws/dashboard 가 읽는다."""
from __future__ import annotations

import time
from collections import deque

from config import settings
from models.schemas import (
    DashboardSnapshot,
    MotorState,
    PipelineRates,
    PodState,
    QueueState,
    RemediationState,
    RollingBuffer,
    RoutingState,
    SvmPoint,
    TempPoint,
    ZoneState,
    epoch_ms,
)


class RateMeter:
    """최근 1초 슬라이딩 윈도우 처리율(msg/s)."""

    def __init__(self, window_s: float = 1.0) -> None:
        self.window_s = window_s
        self._events: deque[tuple[float, int]] = deque()

    def add(self, n: int = 1) -> None:
        self._events.append((time.monotonic(), n))

    def rate(self) -> float:
        cutoff = time.monotonic() - self.window_s
        while self._events and self._events[0][0] < cutoff:
            self._events.popleft()
        return float(sum(n for _, n in self._events)) / self.window_s


class Meters:
    def __init__(self) -> None:
        self.edge = RateMeter()
        self.route_a = RateMeter()
        self.route_b = RateMeter()
        self.drain = RateMeter()
        self.bq = RateMeter()


class StateStore:
    def __init__(self) -> None:
        n = settings.history_points
        self.temp_history: RollingBuffer[TempPoint] = RollingBuffer(n)
        self.svm_history: RollingBuffer[SvmPoint] = RollingBuffer(n)
        self.motor = MotorState()
        self.zones: dict[str, ZoneState] = {
            "ZONE_A": ZoneState(zone="ZONE_A", role="PRIMARY"),
            "ZONE_B": ZoneState(zone="ZONE_B", role="BACKUP"),
        }
        self.routing = RoutingState()
        self.queue = QueueState()
        self.worker_pods: list[PodState] = [
            PodState(id=i + 1, status="ACTIVE" if i < settings.base_workers else "STANDBY")
            for i in range(settings.max_workers)
        ]
        self.remediation = RemediationState()
        self.active_scenarios: set[int] = set()
        self.last_seen: dict[str, float] = {}  # zone / sensor_id → monotonic
        self.meters = Meters()
        self._events: deque[tuple[str, float]] = deque(maxlen=32)

    # ── 이벤트 코드 (프론트 아이콘 점멸용) ─────────────────────
    def push_event(self, code: str) -> None:
        self._events.append((code, time.monotonic()))

    def clear_events(self) -> None:
        self._events.clear()

    def remove_events(self, *codes: str) -> None:
        targets = set(codes)
        self._events = deque([(c, t) for c, t in self._events if c not in targets], maxlen=32)

    def recent_events(self, within_s: float = 5.0) -> list[str]:
        now = time.monotonic()
        out: list[str] = []
        for code, t in self._events:
            if now - t <= within_s and code not in out:
                out.append(code)
        return out

    def active_pod_count(self) -> int:
        return sum(1 for p in self.worker_pods if p.status == "ACTIVE")

    # ── 스냅샷 ──────────────────────────────────────────────
    def snapshot(self, rows_written: int = 0) -> DashboardSnapshot:
        now = time.monotonic()
        zones: dict[str, ZoneState] = {}
        for z, st in self.zones.items():
            seen = self.last_seen.get(z)
            st.last_seen_age_s = round(now - seen, 1) if seen is not None else None
            st.serving = z == self.routing.active_zone
            zones[z] = st.model_copy()

        self.queue.throughput_pct = round(self.active_pod_count() / settings.base_workers * 100)
        self.queue.rows_written = rows_written
        m = self.meters
        pipeline = PipelineRates(
            edge_rate=round(m.edge.rate(), 1),
            route_a_rate=round(m.route_a.rate(), 1),
            route_b_rate=round(m.route_b.rate(), 1),
            drain_rate=round(m.drain.rate(), 1),
            bq_rate=round(m.bq.rate(), 1),
        )
        return DashboardSnapshot(
            ts=epoch_ms(),
            mode=settings.mode,
            active_scenarios=sorted(self.active_scenarios),
            motor=self.motor.model_copy(),
            svm_history=self.svm_history.to_list(),
            temp_history=[p.model_copy() for p in self.temp_history],
            zones=zones,
            routing=self.routing.model_copy(deep=True),
            queue=self.queue.model_copy(),
            pipeline=pipeline,
            worker_pods=[p.model_copy() for p in self.worker_pods],
            remediation=self.remediation.model_copy(deep=True),
            events=self.recent_events(),
        )
