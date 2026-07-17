"""Weather adapter sin red ni persistencia cuando el feature flag está apagado."""

from __future__ import annotations

from wyss_panel_bridge.domain.weather import WeatherError, WeatherForecast


class DisabledWeatherGateway:
    async def forecast(self, location: str, days: int) -> WeatherForecast:
        del location, days
        raise WeatherError("module_disabled", "El clima está desactivado")


class VolatileWeatherCache:
    def __init__(self) -> None:
        self._forecast: WeatherForecast | None = None

    def load(self) -> WeatherForecast | None:
        return self._forecast

    def save(self, forecast: WeatherForecast) -> None:
        self._forecast = forecast
