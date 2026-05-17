from datetime import datetime, timezone
from collections import defaultdict

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


def _owm_id_to_condition(weather_id: int) -> WeatherCondition:
    if 200 <= weather_id <= 232:
        return WeatherCondition.STORM
    if 300 <= weather_id <= 321:
        return WeatherCondition.DRIZZLE
    if 500 <= weather_id <= 504:
        return WeatherCondition.RAIN
    if weather_id == 511:
        return WeatherCondition.SLEET
    if 520 <= weather_id <= 531:
        return WeatherCondition.RAIN
    if 600 <= weather_id <= 622:
        return WeatherCondition.SNOW
    if weather_id in (611, 612, 613, 615, 616):
        return WeatherCondition.SLEET
    if 700 <= weather_id <= 741:
        return WeatherCondition.FOG
    if weather_id == 800:
        return WeatherCondition.CLEAR
    if weather_id == 801:
        return WeatherCondition.PARTLY_CLOUDY
    if weather_id == 802:
        return WeatherCondition.CLOUDY
    if weather_id in (803, 804):
        return WeatherCondition.OVERCAST
    return WeatherCondition.UNKNOWN


class OpenWeatherMapSource(WeatherSource):
    name = "openweathermap"
    base_url = "https://api.openweathermap.org"
    timeout_s = 10

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def get_current(self, lat: float, lon: float) -> WeatherReading:
        params = {"lat": lat, "lon": lon, "appid": self._api_key, "units": "metric", "lang": "ru"}
        data = await self._fetch(f"{self.base_url}/data/2.5/weather", params)
        try:
            return WeatherReading(
                source=self.name,
                location=Location(lat=lat, lon=lon),
                fetched_at=datetime.now(timezone.utc),
                temperature_c=data["main"]["temp"],
                feels_like_c=data["main"]["feels_like"],
                humidity_pct=data["main"]["humidity"],
                pressure_hpa=data["main"]["pressure"],
                wind_speed_ms=data["wind"]["speed"],
                wind_direction_deg=data["wind"].get("deg", 0),
                visibility_km=data.get("visibility", 10000) / 1000.0,
                condition=_owm_id_to_condition(data["weather"][0]["id"]),
                precipitation_mm=data.get("rain", {}).get("1h", 0.0),
                cloud_cover_pct=data["clouds"]["all"],
            )
        except (KeyError, IndexError, TypeError) as e:
            raise SourceParseError(f"OWM parse error: {e}") from e

    async def get_forecast(self, lat: float, lon: float, days: int) -> list[ForecastPoint]:
        params = {"lat": lat, "lon": lon, "appid": self._api_key, "units": "metric", "cnt": days * 8}
        data = await self._fetch(f"{self.base_url}/data/2.5/forecast", params)
        try:
            # Group 3h entries by date → pick midday entry per day
            by_date: dict[str, list[dict]] = defaultdict(list)
            for entry in data["list"]:
                date = entry["dt_txt"][:10]
                by_date[date].append(entry)

            points = []
            for date_str in sorted(by_date)[:days]:
                entries = by_date[date_str]
                # prefer entry closest to noon
                midday = min(entries, key=lambda e: abs(int(e["dt_txt"][11:13]) - 12))
                temps = [e["main"]["temp"] for e in entries]
                points.append(ForecastPoint(
                    target_dt=datetime.fromisoformat(midday["dt_txt"]).replace(tzinfo=timezone.utc),
                    temperature_c=midday["main"]["temp"],
                    temperature_min_c=min(temps),
                    temperature_max_c=max(temps),
                    precipitation_probability_pct=int(midday.get("pop", 0) * 100),
                    precipitation_mm=midday.get("rain", {}).get("3h", 0.0),
                    condition=_owm_id_to_condition(midday["weather"][0]["id"]),
                    wind_speed_ms=midday["wind"]["speed"],
                    confidence=0.0,
                ))
            return points
        except (KeyError, IndexError, TypeError) as e:
            raise SourceParseError(f"OWM forecast parse error: {e}") from e

    async def _fetch(self, url: str, params: dict) -> dict:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                response = await client.get(url, params=params)
        except httpx.TimeoutException as e:
            raise SourceTimeoutError(f"OWM timeout: {e}") from e
        except httpx.RequestError as e:
            raise SourceUnavailableError(f"OWM request error: {e}") from e

        if response.status_code in (401, 403):
            raise SourceAuthError(f"OWM auth error: HTTP {response.status_code}")
        if response.status_code == 429:
            raise SourceRateLimitError("OWM rate limited")
        if response.status_code >= 500:
            raise SourceUnavailableError(f"OWM HTTP {response.status_code}")

        try:
            return response.json()
        except Exception as e:
            raise SourceParseError(f"OWM invalid JSON: {e}") from e
