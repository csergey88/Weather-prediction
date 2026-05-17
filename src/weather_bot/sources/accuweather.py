import time
from datetime import datetime, timezone

import aiosqlite
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

_CACHE_TTL_S = 86400  # 24 hours

# WeatherIcon 1-44 → WeatherCondition
_ICON_CONDITION: dict[int, WeatherCondition] = {
    **{i: WeatherCondition.CLEAR for i in (1, 2, 3, 4, 5)},
    **{i: WeatherCondition.PARTLY_CLOUDY for i in (6, 7, 8)},
    **{i: WeatherCondition.DRIZZLE for i in (9, 10)},
    **{i: WeatherCondition.OVERCAST for i in (11,)},
    **{i: WeatherCondition.PARTLY_CLOUDY for i in (12, 13, 14)},
    **{i: WeatherCondition.STORM for i in (15, 16, 17)},
    **{i: WeatherCondition.RAIN for i in (18,)},
    **{i: WeatherCondition.PARTLY_CLOUDY for i in (19, 20, 21, 22, 23, 24)},
    **{i: WeatherCondition.SNOW for i in (25, 29)},
    **{i: WeatherCondition.RAIN for i in (26,)},
    **{i: WeatherCondition.RAIN for i in (27, 28)},
    **{i: WeatherCondition.STORM for i in (30,)},
    **{i: WeatherCondition.CLEAR for i in (31, 32, 33, 34)},
    **{i: WeatherCondition.PARTLY_CLOUDY for i in (35, 36, 37, 38)},
    **{i: WeatherCondition.STORM for i in (39, 40)},
    **{i: WeatherCondition.RAIN for i in (41, 42)},
    **{i: WeatherCondition.SNOW for i in (43, 44)},
}


def _icon_to_condition(icon: int) -> WeatherCondition:
    return _ICON_CONDITION.get(icon, WeatherCondition.UNKNOWN)


class AccuWeatherSource(WeatherSource):
    name = "accuweather"
    base_url = "https://dataservice.accuweather.com"
    timeout_s = 10

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def _get_db_path(self) -> str:
        from weather_bot.config import settings
        return settings.DB_PATH

    async def _get_location_key(self, lat: float, lon: float) -> str:
        coord_key = f"{lat:.2f}:{lon:.2f}"
        db_path = await self._get_db_path()

        async with aiosqlite.connect(db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS accuweather_location_cache (
                    coord_key TEXT PRIMARY KEY,
                    location_key TEXT NOT NULL,
                    cached_at INTEGER NOT NULL
                )
            """)
            await db.commit()

            cutoff = int(time.time()) - _CACHE_TTL_S
            async with db.execute(
                "SELECT location_key FROM accuweather_location_cache WHERE coord_key = ? AND cached_at > ?",
                (coord_key, cutoff),
            ) as cursor:
                row = await cursor.fetchone()

            if row:
                return row[0]

            # Fetch from API
            location_key = await self._fetch_location_key(lat, lon)

            await db.execute(
                "INSERT OR REPLACE INTO accuweather_location_cache (coord_key, location_key, cached_at) VALUES (?, ?, ?)",
                (coord_key, location_key, int(time.time())),
            )
            await db.commit()
            return location_key

    async def _fetch_location_key(self, lat: float, lon: float) -> str:
        params = {"q": f"{lat},{lon}", "apikey": self._api_key}
        data = await self._fetch(f"{self.base_url}/locations/v1/cities/geoposition/search", params)
        try:
            return data["Key"]
        except (KeyError, TypeError) as e:
            raise SourceParseError(f"AccuWeather location parse error: {e}") from e

    async def get_current(self, lat: float, lon: float) -> WeatherReading:
        key = await self._get_location_key(lat, lon)
        params = {"apikey": self._api_key, "details": "true"}
        data = await self._fetch(f"{self.base_url}/currentconditions/v1/{key}", params)
        try:
            c = data[0]
            temp = c["Temperature"]["Metric"]["Value"]
            feels = c["RealFeelTemperature"]["Metric"]["Value"]
            wind_ms = c["Wind"]["Speed"]["Metric"]["Value"] / 3.6
            wind_deg = c["Wind"]["Direction"]["Degrees"]
            return WeatherReading(
                source=self.name,
                location=Location(lat=lat, lon=lon),
                fetched_at=datetime.now(timezone.utc),
                temperature_c=temp,
                feels_like_c=feels,
                humidity_pct=c.get("RelativeHumidity", 50),
                pressure_hpa=c.get("Pressure", {}).get("Metric", {}).get("Value", 1013.0),
                wind_speed_ms=wind_ms,
                wind_direction_deg=wind_deg,
                visibility_km=c.get("Visibility", {}).get("Metric", {}).get("Value"),
                uv_index=c.get("UVIndex"),
                condition=_icon_to_condition(c["WeatherIcon"]),
                precipitation_mm=c.get("Precip1hr", {}).get("Metric", {}).get("Value", 0.0),
                cloud_cover_pct=c.get("CloudCover", 0),
            )
        except (KeyError, IndexError, TypeError) as e:
            raise SourceParseError(f"AccuWeather current parse error: {e}") from e

    async def get_forecast(self, lat: float, lon: float, days: int) -> list[ForecastPoint]:
        key = await self._get_location_key(lat, lon)
        params = {"apikey": self._api_key, "metric": "true"}
        data = await self._fetch(f"{self.base_url}/forecasts/v1/daily/5day/{key}", params)
        try:
            points = []
            for day in data["DailyForecasts"][:days]:
                dt = datetime.fromtimestamp(day["EpochDate"], tz=timezone.utc)
                t_min = day["Temperature"]["Minimum"]["Value"]
                t_max = day["Temperature"]["Maximum"]["Value"]
                points.append(ForecastPoint(
                    target_dt=dt,
                    temperature_c=(t_min + t_max) / 2,
                    temperature_min_c=t_min,
                    temperature_max_c=t_max,
                    precipitation_probability_pct=int(day["Day"].get("PrecipitationProbability", 0)),
                    precipitation_mm=day["Day"].get("TotalLiquid", {}).get("Value", 0.0),
                    condition=_icon_to_condition(day["Day"]["Icon"]),
                    wind_speed_ms=day["Day"].get("Wind", {}).get("Speed", {}).get("Value", 0.0) / 3.6,
                    confidence=0.0,
                ))
            return points
        except (KeyError, IndexError, TypeError) as e:
            raise SourceParseError(f"AccuWeather forecast parse error: {e}") from e

    async def _fetch(self, url: str, params: dict) -> dict | list:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                response = await client.get(url, params=params)
        except httpx.TimeoutException as e:
            raise SourceTimeoutError(f"AccuWeather timeout: {e}") from e
        except httpx.RequestError as e:
            raise SourceUnavailableError(f"AccuWeather request error: {e}") from e

        if response.status_code in (401, 403):
            raise SourceAuthError(f"AccuWeather auth error: HTTP {response.status_code}")
        if response.status_code == 429:
            raise SourceRateLimitError("AccuWeather rate limited")
        if response.status_code >= 500:
            raise SourceUnavailableError(f"AccuWeather HTTP {response.status_code}")

        try:
            return response.json()
        except Exception as e:
            raise SourceParseError(f"AccuWeather invalid JSON: {e}") from e
