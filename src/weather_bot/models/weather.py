from datetime import datetime
from enum import Enum

from pydantic import BaseModel, field_validator


class WeatherCondition(str, Enum):
    CLEAR = "clear"
    PARTLY_CLOUDY = "partly_cloudy"
    CLOUDY = "cloudy"
    OVERCAST = "overcast"
    RAIN = "rain"
    DRIZZLE = "drizzle"
    SNOW = "snow"
    SLEET = "sleet"
    STORM = "storm"
    FOG = "fog"
    HAIL = "hail"
    UNKNOWN = "unknown"


class Location(BaseModel):
    lat: float
    lon: float
    city: str | None = None
    country: str | None = None
    timezone: str | None = None

    @field_validator("lat")
    @classmethod
    def validate_lat(cls, v: float) -> float:
        if not -90 <= v <= 90:
            raise ValueError("lat must be between -90 and 90")
        return v

    @field_validator("lon")
    @classmethod
    def validate_lon(cls, v: float) -> float:
        if not -180 <= v <= 180:
            raise ValueError("lon must be between -180 and 180")
        return v


class WeatherReading(BaseModel):
    source: str
    location: Location
    fetched_at: datetime
    temperature_c: float
    feels_like_c: float
    humidity_pct: int
    pressure_hpa: float
    wind_speed_ms: float
    wind_direction_deg: int
    visibility_km: float | None = None
    uv_index: float | None = None
    condition: WeatherCondition
    precipitation_mm: float = 0.0
    cloud_cover_pct: int = 0
