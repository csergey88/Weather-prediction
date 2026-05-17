from datetime import datetime, timezone

import httpx

from weather_bot.models.forecast import ForecastPoint
from weather_bot.models.weather import Location, WeatherCondition, WeatherReading
from weather_bot.sources.base import (
    SourceParseError,
    SourceTimeoutError,
    SourceUnavailableError,
    WeatherSource,
)

_WMO_CONDITION: dict[int, WeatherCondition] = {
    0: WeatherCondition.CLEAR,
    1: WeatherCondition.CLEAR,
    2: WeatherCondition.PARTLY_CLOUDY,
    3: WeatherCondition.OVERCAST,
    45: WeatherCondition.FOG,
    48: WeatherCondition.FOG,
    51: WeatherCondition.DRIZZLE,
    53: WeatherCondition.DRIZZLE,
    55: WeatherCondition.DRIZZLE,
    61: WeatherCondition.RAIN,
    63: WeatherCondition.RAIN,
    65: WeatherCondition.RAIN,
    66: WeatherCondition.SLEET,
    67: WeatherCondition.SLEET,
    71: WeatherCondition.SNOW,
    73: WeatherCondition.SNOW,
    75: WeatherCondition.SNOW,
    77: WeatherCondition.SNOW,
    80: WeatherCondition.RAIN,
    81: WeatherCondition.RAIN,
    82: WeatherCondition.RAIN,
    85: WeatherCondition.SNOW,
    86: WeatherCondition.SNOW,
    95: WeatherCondition.STORM,
    96: WeatherCondition.HAIL,
    99: WeatherCondition.HAIL,
}


def _wmo_to_condition(code: int) -> WeatherCondition:
    return _WMO_CONDITION.get(code, WeatherCondition.UNKNOWN)


class OpenMeteoSource(WeatherSource):
    name = "open_meteo"
    base_url = "https://api.open-meteo.com"
    timeout_s = 10

    async def get_current(self, lat: float, lon: float) -> WeatherReading:
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weathercode,windspeed_10m,winddirection_10m,cloudcover,surface_pressure,visibility",
            "wind_speed_unit": "ms",
            "timezone": "auto",
        }
        data = await self._fetch(f"{self.base_url}/v1/forecast", params)
        try:
            c = data["current"]
            return WeatherReading(
                source=self.name,
                location=Location(lat=lat, lon=lon),
                fetched_at=datetime.now(timezone.utc),
                temperature_c=c["temperature_2m"],
                feels_like_c=c.get("apparent_temperature", c["temperature_2m"]),
                humidity_pct=int(c["relative_humidity_2m"]),
                pressure_hpa=c.get("surface_pressure", 1013.0),
                wind_speed_ms=c["windspeed_10m"],
                wind_direction_deg=int(c.get("winddirection_10m", 0)),
                visibility_km=c.get("visibility", 10000.0) / 1000.0,
                condition=_wmo_to_condition(int(c["weathercode"])),
                precipitation_mm=c.get("precipitation", 0.0),
                cloud_cover_pct=int(c.get("cloudcover", 0)),
            )
        except (KeyError, TypeError) as e:
            raise SourceParseError(f"Open-Meteo parse error: {e}") from e

    async def get_forecast(self, lat: float, lon: float, days: int) -> list[ForecastPoint]:
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,weathercode,windspeed_10m_max",
            "forecast_days": days,
            "timezone": "auto",
        }
        data = await self._fetch(f"{self.base_url}/v1/forecast", params)
        try:
            daily = data["daily"]
            points = []
            for i, date_str in enumerate(daily["time"]):
                dt = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
                t_max = daily["temperature_2m_max"][i]
                t_min = daily["temperature_2m_min"][i]
                points.append(ForecastPoint(
                    target_dt=dt,
                    temperature_c=(t_max + t_min) / 2,
                    temperature_min_c=t_min,
                    temperature_max_c=t_max,
                    precipitation_probability_pct=int(daily["precipitation_probability_max"][i] or 0),
                    precipitation_mm=daily["precipitation_sum"][i] or 0.0,
                    condition=_wmo_to_condition(int(daily["weathercode"][i])),
                    wind_speed_ms=daily["windspeed_10m_max"][i],
                    confidence=0.0,
                ))
            return points
        except (KeyError, TypeError, IndexError) as e:
            raise SourceParseError(f"Open-Meteo forecast parse error: {e}") from e

    async def _fetch(self, url: str, params: dict) -> dict:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                response = await client.get(url, params=params)
        except httpx.TimeoutException as e:
            raise SourceTimeoutError(f"Open-Meteo timeout: {e}") from e
        except httpx.RequestError as e:
            raise SourceUnavailableError(f"Open-Meteo request error: {e}") from e

        if response.status_code >= 500:
            raise SourceUnavailableError(f"Open-Meteo HTTP {response.status_code}")
        if response.status_code == 429:
            from weather_bot.sources.base import SourceRateLimitError
            raise SourceRateLimitError("Open-Meteo rate limited")

        try:
            return response.json()
        except Exception as e:
            raise SourceParseError(f"Open-Meteo invalid JSON: {e}") from e
