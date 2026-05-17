from datetime import datetime, timezone

import httpx

from weather_bot.models.forecast import ForecastPoint
from weather_bot.models.weather import Location, WeatherCondition, WeatherReading
from weather_bot.sources.base import (
    SourceAuthError,
    SourceParseError,
    SourceRateLimitError,
    SourceTimeoutError,
    SourceUnavailableError,
    WeatherSource,
)

_CODE_CONDITION: dict[int, WeatherCondition] = {
    1000: WeatherCondition.CLEAR,
    1003: WeatherCondition.PARTLY_CLOUDY,
    1006: WeatherCondition.CLOUDY,
    1009: WeatherCondition.OVERCAST,
    1030: WeatherCondition.FOG,
    1063: WeatherCondition.RAIN,
    1066: WeatherCondition.SNOW,
    1069: WeatherCondition.SLEET,
    1072: WeatherCondition.DRIZZLE,
    1087: WeatherCondition.STORM,
    1114: WeatherCondition.SNOW,
    1117: WeatherCondition.SNOW,
    1135: WeatherCondition.FOG,
    1147: WeatherCondition.FOG,
    1150: WeatherCondition.DRIZZLE,
    1153: WeatherCondition.DRIZZLE,
    1168: WeatherCondition.DRIZZLE,
    1171: WeatherCondition.DRIZZLE,
    1180: WeatherCondition.RAIN,
    1183: WeatherCondition.RAIN,
    1186: WeatherCondition.RAIN,
    1189: WeatherCondition.RAIN,
    1192: WeatherCondition.RAIN,
    1195: WeatherCondition.RAIN,
    1198: WeatherCondition.SLEET,
    1201: WeatherCondition.SLEET,
    1204: WeatherCondition.SLEET,
    1207: WeatherCondition.SLEET,
    1210: WeatherCondition.SNOW,
    1213: WeatherCondition.SNOW,
    1216: WeatherCondition.SNOW,
    1219: WeatherCondition.SNOW,
    1222: WeatherCondition.SNOW,
    1225: WeatherCondition.SNOW,
    1237: WeatherCondition.HAIL,
    1240: WeatherCondition.RAIN,
    1243: WeatherCondition.RAIN,
    1246: WeatherCondition.RAIN,
    1249: WeatherCondition.SLEET,
    1252: WeatherCondition.SLEET,
    1255: WeatherCondition.SNOW,
    1258: WeatherCondition.SNOW,
    1261: WeatherCondition.HAIL,
    1264: WeatherCondition.HAIL,
    1273: WeatherCondition.STORM,
    1276: WeatherCondition.STORM,
    1279: WeatherCondition.STORM,
    1282: WeatherCondition.STORM,
}


def _code_to_condition(code: int) -> WeatherCondition:
    return _CODE_CONDITION.get(code, WeatherCondition.UNKNOWN)


class WeatherAPISource(WeatherSource):
    name = "weatherapi"
    base_url = "https://api.weatherapi.com"
    timeout_s = 10

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def _fetch_forecast(self, lat: float, lon: float, days: int) -> dict:
        params = {"key": self._api_key, "q": f"{lat},{lon}", "days": days, "aqi": "no"}
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                response = await client.get(f"{self.base_url}/v1/forecast.json", params=params)
        except httpx.TimeoutException as e:
            raise SourceTimeoutError(f"WeatherAPI timeout: {e}") from e
        except httpx.RequestError as e:
            raise SourceUnavailableError(f"WeatherAPI request error: {e}") from e

        if response.status_code in (401, 403):
            raise SourceAuthError(f"WeatherAPI auth error: HTTP {response.status_code}")
        if response.status_code == 429:
            raise SourceRateLimitError("WeatherAPI rate limited")
        if response.status_code >= 500:
            raise SourceUnavailableError(f"WeatherAPI HTTP {response.status_code}")

        try:
            return response.json()
        except Exception as e:
            raise SourceParseError(f"WeatherAPI invalid JSON: {e}") from e

    async def get_current(self, lat: float, lon: float) -> WeatherReading:
        data = await self._fetch_forecast(lat, lon, days=1)
        try:
            c = data["current"]
            return WeatherReading(
                source=self.name,
                location=Location(lat=lat, lon=lon),
                fetched_at=datetime.now(timezone.utc),
                temperature_c=c["temp_c"],
                feels_like_c=c["feelslike_c"],
                humidity_pct=c["humidity"],
                pressure_hpa=c["pressure_mb"],
                wind_speed_ms=c["wind_kph"] / 3.6,
                wind_direction_deg=c["wind_degree"],
                visibility_km=c["vis_km"],
                uv_index=c.get("uv"),
                condition=_code_to_condition(c["condition"]["code"]),
                precipitation_mm=c.get("precip_mm", 0.0),
                cloud_cover_pct=c["cloud"],
            )
        except (KeyError, TypeError) as e:
            raise SourceParseError(f"WeatherAPI parse error: {e}") from e

    async def get_forecast(self, lat: float, lon: float, days: int) -> list[ForecastPoint]:
        data = await self._fetch_forecast(lat, lon, days=days)
        try:
            points = []
            for day in data["forecast"]["forecastday"]:
                d = day["day"]
                dt = datetime.fromisoformat(day["date"]).replace(tzinfo=timezone.utc)
                points.append(ForecastPoint(
                    target_dt=dt,
                    temperature_c=(d["maxtemp_c"] + d["mintemp_c"]) / 2,
                    temperature_min_c=d["mintemp_c"],
                    temperature_max_c=d["maxtemp_c"],
                    precipitation_probability_pct=int(d.get("daily_chance_of_rain", 0)),
                    precipitation_mm=d.get("totalprecip_mm", 0.0),
                    condition=_code_to_condition(d["condition"]["code"]),
                    wind_speed_ms=d["maxwind_kph"] / 3.6,
                    confidence=0.0,
                ))
            return points
        except (KeyError, TypeError, IndexError) as e:
            raise SourceParseError(f"WeatherAPI forecast parse error: {e}") from e
