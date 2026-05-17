import pytest
import respx
import httpx

from weather_bot.sources.openweathermap import OpenWeatherMapSource, _owm_id_to_condition
from weather_bot.sources.base import SourceUnavailableError, SourceTimeoutError, SourceRateLimitError, SourceAuthError, SourceParseError
from weather_bot.models.weather import WeatherCondition

BASE = "https://api.openweathermap.org"

CURRENT_RESPONSE = {
    "main": {"temp": 12.0, "feels_like": 9.0, "humidity": 68, "pressure": 1013},
    "wind": {"speed": 5.2, "deg": 315},
    "weather": [{"id": 800, "main": "Clear", "description": "clear sky"}],
    "clouds": {"all": 0},
    "visibility": 10000,
}

FORECAST_RESPONSE = {
    "list": [
        {
            "dt_txt": f"2026-04-2{i} 12:00:00",
            "main": {"temp": 12.0, "feels_like": 9.0, "humidity": 68, "pressure": 1013},
            "wind": {"speed": 5.2, "deg": 315},
            "weather": [{"id": 800}],
            "clouds": {"all": 0},
            "pop": 0.1,
        }
        for i in range(7, 10)
    ]
}


@pytest.mark.asyncio
@respx.mock
async def test_get_current_success():
    respx.get(f"{BASE}/data/2.5/weather").mock(return_value=httpx.Response(200, json=CURRENT_RESPONSE))
    reading = await OpenWeatherMapSource("test-key").get_current(55.75, 37.62)
    assert reading.temperature_c == 12.0
    assert reading.condition == WeatherCondition.CLEAR


@pytest.mark.asyncio
@respx.mock
async def test_get_current_http_error():
    respx.get(f"{BASE}/data/2.5/weather").mock(return_value=httpx.Response(500))
    with pytest.raises(SourceUnavailableError):
        await OpenWeatherMapSource("k").get_current(0, 0)


@pytest.mark.asyncio
@respx.mock
async def test_get_current_timeout():
    respx.get(f"{BASE}/data/2.5/weather").mock(side_effect=httpx.TimeoutException("t"))
    with pytest.raises(SourceTimeoutError):
        await OpenWeatherMapSource("k").get_current(0, 0)


@pytest.mark.asyncio
@respx.mock
async def test_get_current_rate_limit():
    respx.get(f"{BASE}/data/2.5/weather").mock(return_value=httpx.Response(429))
    with pytest.raises(SourceRateLimitError):
        await OpenWeatherMapSource("k").get_current(0, 0)


@pytest.mark.asyncio
@respx.mock
async def test_get_current_auth_error():
    respx.get(f"{BASE}/data/2.5/weather").mock(return_value=httpx.Response(401))
    with pytest.raises(SourceAuthError):
        await OpenWeatherMapSource("k").get_current(0, 0)


@pytest.mark.asyncio
@respx.mock
async def test_get_current_malformed_json():
    respx.get(f"{BASE}/data/2.5/weather").mock(return_value=httpx.Response(200, json={}))
    with pytest.raises(SourceParseError):
        await OpenWeatherMapSource("k").get_current(0, 0)


@pytest.mark.parametrize("weather_id", [200, 300, 500, 511, 600, 611, 700, 800, 801, 802, 803, 804])
def test_normalize_all_condition_codes(weather_id):
    assert _owm_id_to_condition(weather_id) != WeatherCondition.UNKNOWN


@pytest.mark.asyncio
@respx.mock
async def test_get_forecast_returns_correct_days():
    respx.get(f"{BASE}/data/2.5/forecast").mock(return_value=httpx.Response(200, json=FORECAST_RESPONSE))
    points = await OpenWeatherMapSource("k").get_forecast(55.75, 37.62, days=3)
    assert len(points) == 3
