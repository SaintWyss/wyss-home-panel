"""Pronóstico normalizado independiente del proveedor meteorológico."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class WeatherError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class ForecastDay:
    date: str
    code: int
    condition: str
    temperature_min: float
    temperature_max: float
    precipitation_probability: int | None
    precipitation_mm: float
    wind_max_kmh: float


@dataclass(frozen=True, slots=True)
class WeatherForecast:
    location: str
    timezone: str
    provider: str
    observed_at: str
    temperature: float | None
    apparent_temperature: float | None
    code: int | None
    condition: str
    wind_kmh: float | None
    is_day: bool | None
    days: tuple[ForecastDay, ...] = field(default_factory=tuple)
    fetched_at: float = 0.0
    available: bool = True
    stale: bool = False
    error_code: str | None = None

    def projection(self, now: float) -> dict[str, Any]:
        return {
            "location": self.location,
            "timezone": self.timezone,
            "provider": self.provider,
            "observed_at": self.observed_at,
            "fetched_at": self.fetched_at,
            "age_seconds": max(0, int(now - self.fetched_at)),
            "available": self.available,
            "stale": self.stale,
            "error_code": self.error_code,
            "current": {
                "temperature": self.temperature,
                "apparent_temperature": self.apparent_temperature,
                "code": self.code,
                "condition": self.condition,
                "wind_kmh": self.wind_kmh,
                "is_day": self.is_day,
            },
            "days": [
                {
                    "date": day.date,
                    "code": day.code,
                    "condition": day.condition,
                    "temperature_min": day.temperature_min,
                    "temperature_max": day.temperature_max,
                    "precipitation_probability": day.precipitation_probability,
                    "precipitation_mm": day.precipitation_mm,
                    "wind_max_kmh": day.wind_max_kmh,
                }
                for day in self.days
            ],
        }


def weather_condition(code: int) -> str:
    if code == 0:
        return "despejado"
    if code in {1, 2}:
        return "parcialmente_nublado"
    if code == 3:
        return "nublado"
    if code in {45, 48}:
        return "niebla"
    if code in {51, 53, 55, 56, 57}:
        return "llovizna"
    if code in {61, 63, 65, 66, 67, 80, 81, 82}:
        return "lluvia"
    if code in {71, 73, 75, 77, 85, 86}:
        return "nieve"
    if code in {95, 96, 99}:
        return "tormenta"
    return "desconocido"
