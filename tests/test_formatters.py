from datetime import datetime, timezone

import pytest

from weather_bot.bot.formatters import format_confidence_bar, format_current_weather, format_forecast
from weather_bot.models.forecast import AggregatedWeather, ForecastPoint
from weather_bot.models.weather import Location, WeatherCondition, WeatherReading


def _make_reading(source: str = "open_meteo", condition: WeatherCondition = WeatherCondition.CLEAR) -> WeatherReading:
    return WeatherReading(
        source=source,
        location=Location(lat=55.75, lon=37.62, city="Москва", country="Россия"),
        fetched_at=datetime(2026, 4, 26, 20, 0, tzinfo=timezone.utc),
        temperature_c=12.0,
        feels_like_c=9.0,
        humidity_pct=68,
        pressure_hpa=1013.0,
        wind_speed_ms=5.2,
        wind_direction_deg=315,
        visibility_km=10.0,
        condition=condition,
        precipitation_mm=0.0,
        cloud_cover_pct=45,
    )


def _make_agg(readings: list[WeatherReading] | None = None) -> AggregatedWeather:
    reading = _make_reading()
    now = datetime.now(timezone.utc)
    forecast = [
        ForecastPoint(
            target_dt=now,
            temperature_c=12.0,
            temperature_min_c=8.0,
            temperature_max_c=14.0,
            precipitation_probability_pct=60,
            precipitation_mm=0.0,
            condition=WeatherCondition.RAIN,
            wind_speed_ms=4.0,
            confidence=0.82,
        )
    ]
    return AggregatedWeather(
        location=reading.location,
        aggregated_at=now,
        readings=readings or [reading],
        current=reading,
        forecast=forecast,
        source_weights={"open_meteo": 1.0},
    )


def test_format_current_weather_contains_city():
    agg = _make_agg()
    text = format_current_weather(agg)
    assert "Москва" in text


def test_format_current_weather_contains_temperature():
    agg = _make_agg()
    text = format_current_weather(agg)
    assert "+12" in text


def test_format_current_weather_no_visibility_when_none():
    agg = _make_agg()
    agg.current.visibility_km = None
    text = format_current_weather(agg)
    assert "Видимость" not in text


def test_format_forecast_contains_days():
    now = datetime.now(timezone.utc)
    from datetime import timedelta
    points = [
        ForecastPoint(
            target_dt=now + timedelta(days=i),
            temperature_c=10.0,
            temperature_min_c=8.0,
            temperature_max_c=14.0,
            precipitation_probability_pct=20,
            precipitation_mm=0.0,
            condition=WeatherCondition.CLEAR,
            wind_speed_ms=3.0,
            confidence=0.9,
        )
        for i in range(3)
    ]
    text = format_forecast(points, "Москва")
    assert "Москва" in text
    assert len([line for line in text.split("\n") if "°C" in line]) == 3


@pytest.mark.parametrize("confidence,filled", [
    (0.9, 4),
    (1.0, 5),
    (0.3, 2),
    (0.0, 0),
])
def test_confidence_bar(confidence: float, filled: int):
    bar = format_confidence_bar(confidence)
    assert bar.count("█") == filled
    assert bar.count("░") == 5 - filled
    assert str(int(confidence * 100)) in bar
