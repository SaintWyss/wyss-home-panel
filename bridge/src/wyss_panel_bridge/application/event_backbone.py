"""Reanudación, heartbeat y límites del canal de eventos v2."""

from __future__ import annotations

import time
from collections import OrderedDict, deque
from collections.abc import Callable

from wyss_panel_bridge.domain.events import (
    EventDraft,
    RateLimitExceeded,
    ResumeBatch,
)
from wyss_panel_bridge.domain.v2_types import ProjectionEvent
from wyss_panel_bridge.ports_v2 import EventStorePort


class ClientRateLimiter:
    def __init__(
        self,
        limit: int,
        window_seconds: float,
        *,
        max_sources: int = 128,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        if limit <= 0 or window_seconds <= 0 or max_sources <= 0:
            raise ValueError("rate limit inválido")
        self._limit = limit
        self._window = window_seconds
        self._max_sources = max_sources
        self._now = now
        self._hits: OrderedDict[str, deque[float]] = OrderedDict()

    def check(self, source: str) -> None:
        current = self._now()
        hits = self._hits.get(source)
        if hits is None:
            if len(self._hits) >= self._max_sources:
                self._hits.popitem(last=False)
            hits = deque()
            self._hits[source] = hits
        else:
            self._hits.move_to_end(source)
        cutoff = current - self._window
        while hits and hits[0] <= cutoff:
            hits.popleft()
        if len(hits) >= self._limit:
            raise RateLimitExceeded("rate limit excedido")
        hits.append(current)


class SessionHeartbeat:
    def __init__(
        self,
        heartbeat_seconds: float = 12.0,
        missed_before_timeout: int = 2,
        *,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        if heartbeat_seconds <= 0 or missed_before_timeout <= 0:
            raise ValueError("heartbeat inválido")
        self._timeout = heartbeat_seconds * missed_before_timeout
        self._now = now
        self._last_seen = now()

    def beat(self) -> None:
        self._last_seen = self._now()

    def alive(self) -> bool:
        return self._now() - self._last_seen <= self._timeout


class EventBackbone:
    def __init__(self, store: EventStorePort, limiter: ClientRateLimiter) -> None:
        self._store = store
        self._limiter = limiter

    def publish(
        self,
        source: str,
        idempotency_key: str,
        draft: EventDraft,
    ) -> ProjectionEvent:
        self._limiter.check(source)
        return self._store.append(draft, idempotency_key)

    def resume(self, last_event_id: int, limit: int = 256) -> ResumeBatch:
        latest = self._store.latest_event_id()
        if last_event_id == 0 or last_event_id > latest:
            return ResumeBatch(latest, True, ())
        return ResumeBatch(latest, False, self._store.after(last_event_id, limit))
