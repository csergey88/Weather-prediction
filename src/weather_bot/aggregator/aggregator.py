from datetime import datetime, timezone

from weather_bot.models.forecast import AggregatedWeather, ForecastPoint
from weather_bot.models.weather import Location, WeatherCondition, WeatherReading


class MockAggregator:
    """Stub aggregator for bot development without real API keys."""

    async def get_weather(self, lat: float, lon: float) -> AggregatedWeather:
        now = datetime.now(timezone.utc)
        loc = Location(lat=lat, lon=lon, city="Тест", country="RU")
        reading = WeatherReading(
            source="open_meteo",
            location=loc,
            fetched_at=now,
            temperature_c=15.0,
            feels_like_c=13.0,
            humidity_pct=65,
            pressure_hpa=1013.0,
            wind_speed_ms=4.5,
            wind_direction_deg=270,
            visibility_km=10.0,
            condition=WeatherCondition.PARTLY_CLOUDY,
            precipitation_mm=0.0,
            cloud_cover_pct=30,
        )
        forecast = [
            ForecastPoint(
                target_dt=now,
                temperature_c=15.0,
                temperature_min_c=10.0,
                temperature_max_c=18.0,
                precipitation_probability_pct=20,
                precipitation_mm=0.0,
                condition=WeatherCondition.PARTLY_CLOUDY,
                wind_speed_ms=4.5,
                confidence=0.85,
            )
            for _ in range(3)
        ]
        return AggregatedWeather(
            location=loc,
            aggregated_at=now,
            readings=[reading],
            current=reading,
            forecast=forecast,
            source_weights={"open_meteo": 1.0},
            ensemble_version="mock",
        )

    async def get_forecast(self, lat: float, lon: float, days: int) -> AggregatedWeather:
        agg = await self.get_weather(lat, lon)
        from datetime import timedelta
        now = agg.aggregated_at
        agg.forecast = [
            ForecastPoint(
                target_dt=now + timedelta(days=i),
                temperature_c=15.0 + i,
                temperature_min_c=10.0 + i,
                temperature_max_c=18.0 + i,
                precipitation_probability_pct=max(0, 30 - i * 5),
                precipitation_mm=0.0,
                condition=WeatherCondition.PARTLY_CLOUDY,
                wind_speed_ms=4.0,
                confidence=0.8,
            )
            for i in range(days)
        ]
        return agg

    async def health_check(self) -> dict[str, bool]:
        return {"open_meteo": True, "openweathermap": False, "weatherapi": False, "accuweather": False}
