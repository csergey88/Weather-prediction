import pytest
import respx
import httpx

from weather_bot.sources.open_meteo import OpenMeteoSource, _wmo_to_condition
from weather_bot.sources.base import SourceUnavailableError, SourceTimeoutError, SourceRateLimitError, SourceParseError
from weather_bot.models.weather import WeatherCondition

BASE = "https://api.open-meteo.com"

CURRENT_RESPONSE = {
    "current": {
        "temperature_2m": 15.0,
        "apparent_temperature": 13.0,
        "relative_humidity_2m": 65,
        "surface_pressure": 1013.0,
        "windspeed_10m": 4.5,
        "winddirection_10m": 270,
        "visibility": 10000.0,
        "weathercode": 0,
        "precipitation": 0.0,
        "cloudcover": 20,
    }
}

FORECAST_RESPONSE = {
    "daily": {
        "time": ["2026-04-27", "2026-04-28", "2026-04-29"],
        "temperature_2m_max": [18.0, 17.0, 16.0],
        "temperature_2m_min": [10.0, 9.0, 8.0],
        "precipitation_sum": [0.0, 1.0, 2.0],
        "precipitation_probability_max": [10, 40, 60],
        "weathercode": [0, 61, 80],
        "windspeed_10m_max": [4.0, 5.0, 6.0],
    }
}


@pytest.mark.asyncio
@respx.mock
async def test_get_current_success():
    respx.get(f"{BASE}/v1/forecast").mock(return_value=httpx.Response(200, json=CURRENT_RESPONSE))
    source = OpenMeteoSource()
    reading = await source.get_current(55.75, 37.62)
    assert reading.temperature_c == 15.0
    assert reading.humidity_pct == 65
    assert reading.wind_speed_ms == 4.5
    assert reading.condition == WeatherCondition.CLEAR


@pytest.mark.asyncio
@respx.mock
async def test_get_current_http_error():
    respx.get(f"{BASE}/v1/forecast").mock(return_value=httpx.Response(500))
    with pytest.raises(SourceUnavailableError):
        await OpenMeteoSource().get_current(0, 0)


@pytest.mark.asyncio
@respx.mock
async def test_get_current_timeout():
    respx.get(f"{BASE}/v1/forecast").mock(side_effect=httpx.TimeoutException("timeout"))
    with pytest.raises(SourceTimeoutError):
        await OpenMeteoSource().get_current(0, 0)


@pytest.mark.asyncio
@respx.mock
async def test_get_current_rate_limit():
    respx.get(f"{BASE}/v1/forecast").mock(return_value=httpx.Response(429))
    with pytest.raises(SourceRateLimitError):
        await OpenMeteoSource().get_current(0, 0)


@pytest.mark.asyncio
@respx.mock
async def test_get_current_malformed_json():
    respx.get(f"{BASE}/v1/forecast").mock(return_value=httpx.Response(200, json={"unexpected": True}))
    with pytest.raises(SourceParseError):
        await OpenMeteoSource().get_current(0, 0)


@pytest.mark.parametrize("code", [0, 1, 2, 3, 45, 48, 51, 53, 55, 61, 63, 65, 66, 67,
                                    71, 73, 75, 77, 80, 81, 82, 85, 86, 95, 96, 99])
def test_normalize_all_condition_codes(code):
    assert _wmo_to_condition(code) != WeatherCondition.UNKNOWN


@pytest.mark.asyncio
@respx.mock
async def test_get_forecast_returns_correct_days():
    respx.get(f"{BASE}/v1/forecast").mock(return_value=httpx.Response(200, json=FORECAST_RESPONSE))
    points = await OpenMeteoSource().get_forecast(55.75, 37.62, days=3)
    assert len(points) == 3
