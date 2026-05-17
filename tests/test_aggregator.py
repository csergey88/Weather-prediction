from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from weather_bot.aggregator.aggregator import InsufficientSourcesError, WeatherAggregator
from weather_bot.aggregator.weights import normalize_weights
from weather_bot.models.weather import Location, WeatherCondition, WeatherReading
from weather_bot.sources.base import SourceUnavailableError


def _make_reading(source: str, temp: float, condition: WeatherCondition = WeatherCondition.CLEAR) -> WeatherReading:
    return WeatherReading(
        source=source,
        location=Location(lat=55.75, lon=37.62),
        fetched_at=datetime.now(timezone.utc),
        temperature_c=temp,
        feels_like_c=temp - 2,
        humidity_pct=60,
        pressure_hpa=1013.0,
        wind_speed_ms=4.0,
        wind_direction_deg=270,
        condition=condition,
        precipitation_mm=0.0,
        cloud_cover_pct=20,
    )


def _make_source(name: str, temp: float, condition: WeatherCondition = WeatherCondition.CLEAR):
    source = MagicMock()
    source.name = name
    source.get_current = AsyncMock(return_value=_make_reading(name, temp, condition))
    source.get_forecast = AsyncMock(return_value=[])
    source.health_check = AsyncMock(return_value=True)
    return source


@pytest.mark.asyncio
async def test_all_sources_available():
    sources = [
        _make_source("open_meteo", 15.0),
        _make_source("openweathermap", 14.0),
        _make_source("weatherapi", 16.0),
        _make_source("accuweather", 15.5),
    ]
    agg = WeatherAggregator(sources, min_sources=2)
    result = await agg.get_weather(55.75, 37.62)
    assert len(result.readings) == 4
    assert 14.0 <= result.current.temperature_c <= 16.0


@pytest.mark.asyncio
async def test_one_source_fails():
    sources = [
        _make_source("open_meteo", 15.0),
        _make_source("openweathermap", 14.0),
        _make_source("weatherapi", 16.0),
    ]
    sources.append(MagicMock())
    sources[-1].name = "accuweather"
    sources[-1].get_current = AsyncMock(side_effect=SourceUnavailableError("down"))
    sources[-1].health_check = AsyncMock(return_value=False)

    agg = WeatherAggregator(sources, min_sources=2)
    result = await agg.get_weather(55.75, 37.62)
    assert len(result.readings) == 3


@pytest.mark.asyncio
async def test_below_min_sources():
    sources = [
        _make_source("open_meteo", 15.0),
    ]
    fail = MagicMock()
    fail.name = "openweathermap"
    fail.get_current = AsyncMock(side_effect=SourceUnavailableError("down"))
    sources.append(fail)

    agg = WeatherAggregator(sources, min_sources=2)
    with pytest.raises(InsufficientSourcesError):
        await agg.get_weather(55.75, 37.62)


def test_weights_sum_to_one():
    weights = normalize_weights(["open_meteo", "openweathermap", "weatherapi", "accuweather"])
    assert abs(sum(weights.values()) - 1.0) < 1e-9


def test_weights_sum_to_one_partial():
    weights = normalize_weights(["open_meteo", "openweathermap"])
    assert abs(sum(weights.values()) - 1.0) < 1e-9


@pytest.mark.asyncio
async def test_condition_majority_vote():
    sources = [
        _make_source("open_meteo", 15.0, WeatherCondition.RAIN),
        _make_source("openweathermap", 14.0, WeatherCondition.RAIN),
        _make_source("weatherapi", 16.0, WeatherCondition.RAIN),
        _make_source("accuweather", 15.5, WeatherCondition.CLOUDY),
    ]
    agg = WeatherAggregator(sources, min_sources=2)
    result = await agg.get_weather(55.75, 37.62)
    assert result.current.condition == WeatherCondition.RAIN
