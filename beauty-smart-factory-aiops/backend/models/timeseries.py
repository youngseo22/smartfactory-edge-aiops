"""인메모리 시계열 버퍼 (BigQuery 실시간 뷰 대체).

- BucketedTimeSeries: Event-Time 기준 1초 버킷 · 최근 N 포인트 슬라이딩 윈도우.
  늦게 도착한(store-and-forward 재전송) 데이터도 원래 시각의 버킷을 채우므로
  Failover 이후 그래프 공백이 메워지며 "데이터 유실 0%"를 시각적으로 증명한다.
- RateMeter: 최근 window 초 동안의 처리량(msg/s).
"""
from __future__ import annotations

import time
from collections import deque
from typing import Any, Iterable, Optional


class RateMeter:
    def __init__(self, window_s: float = 2.0) -> None:
        self.window_s = window_s
        self._events: deque[tuple[float, int]] = deque()
        self.total = 0

    def mark(self, n: int = 1, now: Optional[float] = None) -> None:
        if n <= 0:
            return
        now = now if now is not None else time.time()
        self._events.append((now, n))
        self.total += n
        self._trim(now)

    def _trim(self, now: float) -> None:
        cutoff = now - self.window_s
        while self._events and self._events[0][0] < cutoff:
            self._events.popleft()

    def rate(self, now: Optional[float] = None) -> float:
        now = now if now is not None else time.time()
        self._trim(now)
        return round(sum(n for _, n in self._events) / self.window_s, 1)


class BucketedTimeSeries:
    def __init__(self, bucket_s: float = 1.0, points: int = 30) -> None:
        self.bucket_s = bucket_s
        self.points = points
        self._buckets: dict[int, dict[str, Any]] = {}

    def update(self, ts: float, **fields: Any) -> None:
        key = int(ts // self.bucket_s)
        self._buckets.setdefault(key, {}).update(fields)

    def window(self, fields: Iterable[str], now: Optional[float] = None) -> list[dict[str, Any]]:
        now = now if now is not None else time.time()
        # 현재 진행 중인 버킷의 순간 공백(flicker)을 피하기 위해 살짝 이전 시점까지만
        end = int((now - 0.3) // self.bucket_s)
        start = end - self.points + 1
        for k in [k for k in self._buckets if k < start - 2]:
            del self._buckets[k]
        fields = tuple(fields)
        out: list[dict[str, Any]] = []
        for k in range(start, end + 1):
            bucket = self._buckets.get(k, {})
            row: dict[str, Any] = {"t": round(k * self.bucket_s, 3)}
            for f in fields:
                row[f] = bucket.get(f)
            out.append(row)
        return out

    def clear(self) -> None:
        self._buckets.clear()
