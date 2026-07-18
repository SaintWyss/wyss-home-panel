from __future__ import annotations

import sqlite3
from dataclasses import replace
from pathlib import Path

import httpx
import pytest

from wyss_panel_bridge.adapters.open_meteo import OpenMeteoGateway
from wyss_panel_bridge.adapters.sqlite_events import SqliteEventStore
from wyss_panel_bridge.adapters.sqlite_weather_cache import SqliteWeatherCache
from wyss_panel_bridge.application.weather_service import WeatherService
from wyss_panel_bridge.domain.weather import ForecastDay, WeatherError, WeatherForecast


def _provider_payload() -> dict[str, object]:
    return {
        "timezone": "America/Argentina/Cordoba",
        "current": {
            "time": "2026-07-17T20:45",
            "temperature_2m": 28.5,
            "apparent_temperature": 29.1,
            "weather_code": 0,
            "wind_speed_10m": 8.2,
            "is_day": 1,
        },
        "daily": {
            "time": [f"2026-07-{day:02d}" for day in range(17, 24)],
            "weather_code": [0, 1, 2, 3, 61, 95, 45],
            "temperature_2m_max": [28, 29, 27, 25, 22, 24, 26],
            "temperature_2m_min": [15, 16, 14, 13, 12, 13, 14],
            "precipitation_probability_max": [0, 10, 20, 30, 80, 70, None],
            "precipitation_sum": [0, 0, 0.2, 0, 12.4, 4.0, 0],
            "wind_speed_10m_max": [12, 14, 16, 18, 22, 30, 10],
        },
    }


@pytest.mark.asyncio
async def test_open_meteo_requests_fixed_location_timezone_and_seven_days() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=_provider_payload())

    gateway = OpenMeteoGateway(
        -27.4514,
        -58.9867,
        "America/Argentina/Cordoba",
        transport=httpx.MockTransport(handler),
        now=lambda: 1000.0,
    )
    forecast = await gateway.forecast("Resistencia, Chaco", 7)

    assert len(forecast.days) == 7
    assert forecast.condition == "despejado"
    assert forecast.days[4].condition == "lluvia"
    assert forecast.days[5].condition == "tormenta"
    assert forecast.days[6].precipitation_probability is None
    params = requests[0].url.params
    assert params["forecast_days"] == "7"
    assert params["timezone"] == "America/Argentina/Cordoba"
    assert params["latitude"] == "-27.4514"
    assert params["longitude"] == "-58.9867"


@pytest.mark.asyncio
async def test_open_meteo_rejects_missing_values_and_wrong_timezone() -> None:
    malformed = _provider_payload()
    malformed["timezone"] = "UTC"
    gateway = OpenMeteoGateway(
        -27.4514,
        -58.9867,
        "America/Argentina/Cordoba",
        transport=httpx.MockTransport(lambda _request: httpx.Response(200, json=malformed)),
    )

    with pytest.raises(WeatherError) as captured:
        await gateway.forecast("Resistencia, Chaco", 7)

    assert captured.value.code == "invalid_forecast"


def _forecast(fetched_at: float) -> WeatherForecast:
    return WeatherForecast(
        location="Resistencia, Chaco",
        timezone="America/Argentina/Cordoba",
        provider="open-meteo",
        observed_at="2026-07-17T20:45",
        temperature=28.5,
        apparent_temperature=29.1,
        code=0,
        condition="despejado",
        wind_kmh=8.2,
        is_day=True,
        days=(ForecastDay("2026-07-17", 0, "despejado", 15, 28, 0, 0, 12),) * 7,
        fetched_at=fetched_at,
    )


class FakeWeather:
    def __init__(self, forecast: WeatherForecast) -> None:
        self.value = forecast
        self.failure: WeatherError | None = None
        self.calls = 0

    async def forecast(self, location: str, days: int) -> WeatherForecast:
        assert location == "Resistencia, Chaco" and days == 7
        self.calls += 1
        if self.failure is not None:
            raise self.failure
        return self.value


@pytest.mark.asyncio
async def test_weather_service_persists_then_uses_explicit_stale_cache(tmp_path: Path) -> None:
    cache = SqliteWeatherCache(tmp_path / "weather.sqlite3")
    gateway = FakeWeather(_forecast(1000))
    service = WeatherService(
        gateway,
        cache,
        SqliteEventStore(tmp_path / "events.sqlite3"),
        refresh_seconds=60,
        max_stale_seconds=7200,
        now=lambda: 1000,
    )
    fresh = await service.ensure_snapshot()
    assert fresh is not None and fresh.payload["stale"] is False

    offline = FakeWeather(_forecast(1000))
    offline.failure = WeatherError("provider_unavailable", "offline")
    restarted = WeatherService(
        offline,
        cache,
        SqliteEventStore(tmp_path / "events.sqlite3"),
        refresh_seconds=60,
        max_stale_seconds=7200,
        now=lambda: 4600,
    )
    stale = await restarted.ensure_snapshot()

    assert stale is not None
    assert stale.payload["available"] is True
    assert stale.payload["stale"] is True
    assert stale.payload["age_seconds"] == 3600
    assert len(stale.payload["days"]) == 7
    assert stale.payload["error_code"] == "provider_unavailable"


@pytest.mark.asyncio
async def test_weather_service_expires_cache_and_backoffs_without_event_storm(
    tmp_path: Path,
) -> None:
    cache = SqliteWeatherCache(tmp_path / "weather.sqlite3")
    cache.save(_forecast(1000))
    gateway = FakeWeather(_forecast(1000))
    gateway.failure = WeatherError("provider_unavailable", "offline")
    service = WeatherService(
        gateway,
        cache,
        SqliteEventStore(tmp_path / "events.sqlite3"),
        refresh_seconds=60,
        max_stale_seconds=7200,
        now=lambda: 9000,
    )

    expired = await service.ensure_snapshot()
    duplicate = await service.ensure_snapshot()

    assert expired is not None
    assert expired.payload["available"] is False
    assert expired.payload["stale"] is True
    assert expired.payload["days"] == []
    assert expired.payload["error_code"] == "cache_expired"
    assert duplicate is None
    assert gateway.calls == 1


def test_sqlite_weather_cache_round_trips_private_file(tmp_path: Path) -> None:
    path = tmp_path / "weather.sqlite3"
    cache = SqliteWeatherCache(path)
    expected = replace(_forecast(1000), stale=True, error_code="provider_unavailable")
    cache.save(expected)

    assert cache.load() == expected
    assert path.stat().st_mode & 0o777 == 0o600


@pytest.mark.asyncio
async def test_corrupt_cache_degrades_to_explicit_provider_failure(tmp_path: Path) -> None:
    path = tmp_path / "weather.sqlite3"
    cache = SqliteWeatherCache(path)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO weather_cache (singleton, payload_json) VALUES (1, ?)",
            ("{invalid",),
        )
    gateway = FakeWeather(_forecast(1000))
    gateway.failure = WeatherError("provider_unavailable", "offline")
    service = WeatherService(
        gateway,
        cache,
        SqliteEventStore(tmp_path / "events.sqlite3"),
        refresh_seconds=60,
        max_stale_seconds=7200,
        now=lambda: 1000,
    )

    event = await service.ensure_snapshot()

    assert event is not None
    assert event.payload["available"] is False
    assert event.payload["days"] == []
    assert event.payload["error_code"] == "provider_unavailable"
