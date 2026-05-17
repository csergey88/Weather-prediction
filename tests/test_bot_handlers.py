from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from weather_bot.models.forecast import AggregatedWeather, ForecastPoint
from weather_bot.models.weather import Location, WeatherCondition, WeatherReading


def _make_agg(city: str = "Москва", days: int = 3) -> AggregatedWeather:
    now = datetime.now(timezone.utc)
    loc = Location(lat=55.75, lon=37.62, city=city, country="Россия")
    reading = WeatherReading(
        source="open_meteo",
        location=loc,
        fetched_at=now,
        temperature_c=15.0,
        feels_like_c=13.0,
        humidity_pct=60,
        pressure_hpa=1013.0,
        wind_speed_ms=4.0,
        wind_direction_deg=270,
        condition=WeatherCondition.CLEAR,
        precipitation_mm=0.0,
        cloud_cover_pct=20,
    )
    forecast = [
        ForecastPoint(
            target_dt=now + timedelta(days=i),
            temperature_c=15.0,
            temperature_min_c=10.0,
            temperature_max_c=18.0,
            precipitation_probability_pct=20,
            precipitation_mm=0.0,
            condition=WeatherCondition.CLEAR,
            wind_speed_ms=4.0,
            confidence=0.85,
        )
        for i in range(days)
    ]
    return AggregatedWeather(
        location=loc,
        aggregated_at=now,
        readings=[reading],
        current=reading,
        forecast=forecast,
        source_weights={"open_meteo": 1.0},
    )


def _make_message(text: str, user_id: int = 1) -> MagicMock:
    msg = MagicMock()
    msg.text = text
    msg.from_user = MagicMock()
    msg.from_user.id = user_id
    msg.answer = AsyncMock()
    return msg


@pytest.mark.asyncio
async def test_weather_command_valid_city():
    from weather_bot.bot.handlers import cmd_weather
    from weather_bot.models.weather import Location

    msg = _make_message("/weather Москва")
    agg = _make_agg("Москва")

    with (
        patch("weather_bot.bot.handlers.geocode", new=AsyncMock(return_value=Location(lat=55.75, lon=37.62, city="Москва", country="Россия"))),
        patch("weather_bot.bot.handlers._aggregator.get_weather", new=AsyncMock(return_value=agg)),
    ):
        await cmd_weather(msg)

    msg.answer.assert_called_once()
    call_text = msg.answer.call_args[0][0]
    assert "Москва" in call_text


@pytest.mark.asyncio
async def test_weather_command_no_city_no_saved_location():
    from weather_bot.bot.handlers import cmd_weather

    msg = _make_message("/weather")

    with patch("weather_bot.bot.handlers.get_user_location", new=AsyncMock(return_value=None)):
        await cmd_weather(msg)

    msg.answer.assert_called_once()
    assert "город" in msg.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_weather_command_unknown_city():
    from weather_bot.bot.handlers import cmd_weather
    from weather_bot.utils.geo import CityNotFoundError

    msg = _make_message("/weather xyzabc123")

    with patch("weather_bot.bot.handlers.geocode", new=AsyncMock(side_effect=CityNotFoundError("not found"))):
        await cmd_weather(msg)

    msg.answer.assert_called_once()
    assert "не найден" in msg.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_forecast_days_clamped():
    from weather_bot.bot.handlers import cmd_forecast
    from weather_bot.models.weather import Location

    msg = _make_message("/forecast Москва 10")
    agg = _make_agg("Москва", days=7)

    mock_get_forecast = AsyncMock(return_value=agg)
    with (
        patch("weather_bot.bot.handlers.geocode", new=AsyncMock(return_value=Location(lat=55.75, lon=37.62, city="Москва"))),
        patch("weather_bot.bot.handlers._aggregator.get_forecast", new=mock_get_forecast),
    ):
        await cmd_forecast(msg)

    called_days = mock_get_forecast.call_args[0][2]
    assert called_days == 7


@pytest.mark.asyncio
async def test_set_location_saves_to_db(tmp_db):
    from weather_bot.bot.handlers import handle_location
    from weather_bot.storage.db import get_user_location, init_db

    await init_db()

    msg = MagicMock()
    msg.location = MagicMock()
    msg.location.latitude = 55.75
    msg.location.longitude = 37.62
    msg.from_user = MagicMock()
    msg.from_user.id = 42
    msg.answer = AsyncMock()

    state = AsyncMock()
    state.clear = AsyncMock()

    from weather_bot.models.weather import Location
    with patch("weather_bot.bot.handlers.geocode", new=AsyncMock(return_value=Location(lat=55.75, lon=37.62, city="Москва"))):
        await handle_location(msg, state)

    saved = await get_user_location(42)
    assert saved is not None
    assert abs(saved.lat - 55.75) < 0.01


@pytest.mark.asyncio
async def test_sources_command():
    from weather_bot.bot.handlers import cmd_sources

    msg = _make_message("/sources")
    with patch("weather_bot.bot.handlers._aggregator.health_check", new=AsyncMock(return_value={
        "openweathermap": True, "weatherapi": True, "accuweather": True, "open_meteo": True,
    })):
        await cmd_sources(msg)

    msg.answer.assert_called_once()
    text = msg.answer.call_args[0][0]
    for abbr in ["OWM", "WA", "ACW", "OM"]:
        assert abbr in text
