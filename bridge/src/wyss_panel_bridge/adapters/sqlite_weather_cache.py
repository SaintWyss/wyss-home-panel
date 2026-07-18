"""Último pronóstico válido durable, sin autoridad sobre su frescura."""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

from wyss_panel_bridge.domain.weather import ForecastDay, WeatherForecast


class SqliteWeatherCache:
    def __init__(self, path: Path) -> None:
        self._path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS weather_cache (
                    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                    payload_json TEXT NOT NULL
                )
                """
            )
        os.chmod(path, 0o600)

    def load(self) -> WeatherForecast | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM weather_cache WHERE singleton = 1"
            ).fetchone()
        if row is None:
            return None
        try:
            decoded = json.loads(str(row[0]))
        except (json.JSONDecodeError, TypeError) as error:
            raise RuntimeError("cache meteorológico corrupto") from error
        if not isinstance(decoded, dict):
            raise RuntimeError("cache meteorológico corrupto")
        raw = cast(dict[str, Any], decoded)
        raw_days = raw.pop("days", None)
        if not isinstance(raw_days, list):
            raise RuntimeError("cache meteorológico corrupto")
        try:
            days = tuple(ForecastDay(**item) for item in raw_days if isinstance(item, dict))
            if len(days) != len(raw_days):
                raise TypeError
            return WeatherForecast(days=days, **raw)
        except (TypeError, ValueError) as error:
            raise RuntimeError("cache meteorológico corrupto") from error

    def save(self, forecast: WeatherForecast) -> None:
        encoded = json.dumps(asdict(forecast), sort_keys=True, separators=(",", ":"))
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO weather_cache (singleton, payload_json) VALUES (1, ?)
                ON CONFLICT(singleton) DO UPDATE SET payload_json = excluded.payload_json
                """,
                (encoded,),
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path, timeout=5.0)
