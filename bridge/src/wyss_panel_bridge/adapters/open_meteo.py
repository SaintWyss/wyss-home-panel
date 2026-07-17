"""Adapter estricto para el Forecast API público de Open-Meteo."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any, cast

import httpx

from wyss_panel_bridge.domain.weather import (
    ForecastDay,
    WeatherError,
    WeatherForecast,
    weather_condition,
)


class OpenMeteoGateway:
    def __init__(
        self,
        latitude: float,
        longitude: float,
        timezone: str,
        *,
        url: str = "https://api.open-meteo.com",
        transport: httpx.AsyncBaseTransport | None = None,
        now: Callable[[], float] = time.time,
    ) -> None:
        self._latitude = latitude
        self._longitude = longitude
        self._timezone = timezone
        self._now = now
        self._client = httpx.AsyncClient(base_url=url, timeout=12.0, transport=transport)

    async def forecast(self, location: str, days: int) -> WeatherForecast:
        if location != "Resistencia, Chaco" or days != 7:
            raise WeatherError("invalid_location", "La ubicación meteorológica no está permitida")
        params: dict[str, str | int | float] = {
            "latitude": self._latitude,
            "longitude": self._longitude,
            "timezone": self._timezone,
            "forecast_days": 7,
            "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m,is_day",
            "daily": (
                "weather_code,temperature_2m_max,temperature_2m_min,"
                "precipitation_probability_max,precipitation_sum,wind_speed_10m_max"
            ),
        }
        try:
            response = await self._client.get("/v1/forecast", params=params)
            response.raise_for_status()
            decoded = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise WeatherError("provider_unavailable", "Open-Meteo no respondió") from error
        if not isinstance(decoded, dict):
            raise WeatherError("invalid_forecast", "Open-Meteo devolvió un pronóstico inválido")
        return self._decode(cast(dict[str, Any], decoded), location)

    def _decode(self, raw: dict[str, Any], location: str) -> WeatherForecast:
        if raw.get("timezone") != self._timezone:
            raise WeatherError("invalid_forecast", "Open-Meteo devolvió otra zona horaria")
        current = raw.get("current")
        daily = raw.get("daily")
        if not isinstance(current, dict) or not isinstance(daily, dict):
            raise WeatherError("invalid_forecast", "Open-Meteo devolvió un pronóstico incompleto")
        dates = self._seven(daily, "time")
        codes = self._seven(daily, "weather_code")
        maximums = self._seven(daily, "temperature_2m_max")
        minimums = self._seven(daily, "temperature_2m_min")
        probabilities = self._seven(daily, "precipitation_probability_max")
        precipitation = self._seven(daily, "precipitation_sum")
        winds = self._seven(daily, "wind_speed_10m_max")
        forecast_days = tuple(
            ForecastDay(
                date=self._text(dates[index]),
                code=self._integer(codes[index], 0, 99),
                condition=weather_condition(self._integer(codes[index], 0, 99)),
                temperature_min=self._number(minimums[index], -100, 100),
                temperature_max=self._number(maximums[index], -100, 100),
                precipitation_probability=self._optional_integer(probabilities[index], 0, 100),
                precipitation_mm=self._number(precipitation[index], 0, 10_000),
                wind_max_kmh=self._number(winds[index], 0, 500),
            )
            for index in range(7)
        )
        code = self._integer(current.get("weather_code"), 0, 99)
        return WeatherForecast(
            location=location,
            timezone=self._timezone,
            provider="open-meteo",
            observed_at=self._text(current.get("time")),
            temperature=self._number(current.get("temperature_2m"), -100, 100),
            apparent_temperature=self._number(current.get("apparent_temperature"), -100, 100),
            code=code,
            condition=weather_condition(code),
            wind_kmh=self._number(current.get("wind_speed_10m"), 0, 500),
            is_day=self._integer(current.get("is_day"), 0, 1) == 1,
            days=forecast_days,
            fetched_at=self._now(),
        )

    @staticmethod
    def _text(value: Any) -> str:
        if not isinstance(value, str) or not value or len(value) > 64:
            raise WeatherError("invalid_forecast", "Open-Meteo devolvió texto inválido")
        return value

    @staticmethod
    def _seven(value: dict[str, Any], key: str) -> list[Any]:
        items = value.get(key)
        if not isinstance(items, list) or len(items) != 7:
            raise WeatherError("invalid_forecast", "Open-Meteo no devolvió siete días")
        return items

    @staticmethod
    def _number(value: Any, minimum: float, maximum: float) -> float:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise WeatherError("invalid_forecast", "Open-Meteo devolvió un valor inválido")
        number = float(value)
        if not minimum <= number <= maximum:
            raise WeatherError("invalid_forecast", "Open-Meteo devolvió un valor fuera de rango")
        return number

    @classmethod
    def _integer(cls, value: Any, minimum: int, maximum: int) -> int:
        number = cls._number(value, minimum, maximum)
        if not number.is_integer():
            raise WeatherError("invalid_forecast", "Open-Meteo devolvió un entero inválido")
        return int(number)

    @classmethod
    def _optional_integer(cls, value: Any, minimum: int, maximum: int) -> int | None:
        return None if value is None else cls._integer(value, minimum, maximum)
