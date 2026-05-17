import statistics
from collections import defaultdict

from weather_bot.models.weather import WeatherCondition, WeatherReading

_NUMERIC_FIELDS = (
    "temperature_c",
    "feels_like_c",
    "humidity_pct",
    "pressure_hpa",
    "wind_speed_ms",
    "precipitation_mm",
    "cloud_cover_pct",
)


def weighted_average(readings: list[WeatherReading], weights: dict[str, float]) -> dict:
    result: dict[str, float] = {}
    for field in _NUMERIC_FIELDS:
        total_w = sum(weights[r.source] for r in readings)
        result[field] = sum(getattr(r, field) * weights[r.source] for r in readings) / total_w

    # wind_direction_deg — circular mean via unit vectors
    import math
    sin_sum = sum(math.sin(math.radians(r.wind_direction_deg)) * weights[r.source] for r in readings)
    cos_sum = sum(math.cos(math.radians(r.wind_direction_deg)) * weights[r.source] for r in readings)
    result["wind_direction_deg"] = int(math.degrees(math.atan2(sin_sum, cos_sum)) % 360)

    # visibility_km — weighted average of non-None values
    vis_readings = [(r, weights[r.source]) for r in readings if r.visibility_km is not None]
    if vis_readings:
        vis_w = sum(w for _, w in vis_readings)
        result["visibility_km"] = sum(r.visibility_km * w for r, w in vis_readings) / vis_w  # type: ignore[operator]
    else:
        result["visibility_km"] = None  # type: ignore[assignment]

    return result


def majority_condition(readings: list[WeatherReading], weights: dict[str, float]) -> WeatherCondition:
    scores: dict[WeatherCondition, float] = defaultdict(float)
    for r in readings:
        scores[r.condition] += weights[r.source]
    return max(scores, key=lambda c: scores[c])


def compute_confidence(readings: list[WeatherReading], threshold: float = 3.0) -> float:
    if len(readings) < 2:
        return 1.0
    std = statistics.stdev(r.temperature_c for r in readings)
    return max(0.0, min(1.0, 1.0 - std / threshold))
