from datetime import datetime

from pydantic import BaseModel, field_validator

from weather_bot.models.weather import Location, WeatherCondition, WeatherReading


class ForecastPoint(BaseModel):
    target_dt: datetime
    temperature_c: float
    temperature_min_c: float
    temperature_max_c: float
    precipitation_probability_pct: int
    precipitation_mm: float
    condition: WeatherCondition
    wind_speed_ms: float
    confidence: float

    @field_validator("precipitation_probability_pct")
    @classmethod
    def clamp_precip_pct(cls, v: int) -> int:
        return max(0, min(100, v))

    @field_validator("confidence")
    @classmethod
    def clamp_confidence(cls, v: float) -> float:
        return max(0.0, min(1.0, v))


class AggregatedWeather(BaseModel):
    location: Location
    aggregated_at: datetime
    readings: list[WeatherReading]
    current: WeatherReading
    forecast: list[ForecastPoint]
    source_weights: dict[str, float]
    ensemble_version: str = "v1_ridge"
