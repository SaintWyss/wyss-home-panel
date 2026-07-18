"""Refresco, cache offline y proyección explícita del clima."""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import replace

from wyss_panel_bridge.domain.events import EventDraft
from wyss_panel_bridge.domain.v2_types import ProjectionEvent
from wyss_panel_bridge.domain.weather import WeatherError, WeatherForecast
from wyss_panel_bridge.ports_v2 import EventStorePort, WeatherCachePort, WeatherPort

EventSink = Callable[[ProjectionEvent], Awaitable[None]]


class WeatherService:
    def __init__(
        self,
        weather: WeatherPort,
        cache: WeatherCachePort,
        events: EventStorePort,
        *,
        refresh_seconds: float = 30 * 60,
        max_stale_seconds: float = 6 * 60 * 60,
        now: Callable[[], float] = time.time,
    ) -> None:
        if refresh_seconds <= 0 or max_stale_seconds < refresh_seconds:
            raise ValueError("ventanas de clima inválidas")
        self._weather = weather
        self._cache = cache
        self._events = events
        self._refresh_seconds = refresh_seconds
        self._max_stale_seconds = max_stale_seconds
        self._now = now
        self._lock = asyncio.Lock()
        self._current: WeatherForecast | None = None
        self._last_attempt = 0.0
        self._last_payload: dict[str, object] | None = None
        self._event_sink: EventSink | None = None

    def set_event_sink(self, sink: EventSink | None) -> None:
        self._event_sink = sink

    async def ensure_snapshot(self) -> ProjectionEvent | None:
        async with self._lock:
            current_time = self._now()
            if self._current is None:
                try:
                    self._current = self._cache.load()
                except RuntimeError:
                    self._current = None
            if (
                self._current is not None
                and current_time - self._last_attempt < self._refresh_seconds
            ):
                if self._last_payload is not None:
                    return None
                return await self._publish(self._current, current_time)
            if (
                self._current is not None
                and current_time - self._current.fetched_at < self._refresh_seconds
            ):
                self._last_attempt = current_time
                return await self._publish(self._current, current_time)
            self._last_attempt = current_time
            try:
                forecast = await self._weather.forecast("Resistencia, Chaco", 7)
            except WeatherError as error:
                forecast = self._fallback(error, current_time)
            else:
                forecast = replace(forecast, stale=False, error_code=None, available=True)
                self._cache.save(forecast)
            self._current = forecast
            return await self._publish(forecast, current_time)

    def _fallback(self, error: WeatherError, current_time: float) -> WeatherForecast:
        if self._current is not None:
            age = current_time - self._current.fetched_at
            if age <= self._max_stale_seconds:
                return replace(self._current, stale=True, error_code=error.code, available=True)
        return WeatherForecast(
            location="Resistencia, Chaco",
            timezone="America/Argentina/Cordoba",
            provider="open-meteo",
            observed_at="",
            temperature=None,
            apparent_temperature=None,
            code=None,
            condition="sin_datos",
            wind_kmh=None,
            is_day=None,
            fetched_at=self._current.fetched_at if self._current is not None else current_time,
            available=False,
            stale=self._current is not None,
            error_code="cache_expired" if self._current is not None else error.code,
        )

    async def _publish(
        self, forecast: WeatherForecast, current_time: float
    ) -> ProjectionEvent | None:
        payload: dict[str, object] = forecast.projection(current_time)
        if payload == self._last_payload:
            return None
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        key = f"weather:{hashlib.sha256(encoded.encode()).hexdigest()[:48]}"
        event = self._events.append(
            EventDraft("weather.forecast.changed", "weather", payload),
            key,
        )
        self._last_payload = payload
        if self._event_sink is not None:
            await self._event_sink(event)
        return event
