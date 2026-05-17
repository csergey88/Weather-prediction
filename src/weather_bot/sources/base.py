from abc import ABC, abstractmethod

from weather_bot.models.forecast import ForecastPoint
from weather_bot.models.weather import WeatherReading


class WeatherSourceError(Exception):
    pass


class SourceUnavailableError(WeatherSourceError):
    pass


class SourceTimeoutError(WeatherSourceError):
    pass


class SourceRateLimitError(WeatherSourceError):
    pass


class SourceAuthError(WeatherSourceError):
    pass


class SourceParseError(WeatherSourceError):
    pass


class WeatherSource(ABC):
    name: str
    base_url: str
    timeout_s: int = 10

    @abstractmethod
    async def get_current(self, lat: float, lon: float) -> WeatherReading: ...

    @abstractmethod
    async def get_forecast(self, lat: float, lon: float, days: int) -> list[ForecastPoint]: ...

    async def health_check(self) -> bool:
        try:
            await self.get_current(0.0, 0.0)
            return True
        except Exception:
            return False
