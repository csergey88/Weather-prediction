import pytest
import respx
import httpx

from weather_bot.sources.weatherapi import WeatherAPISource, _code_to_condition
from weather_bot.sources.base import SourceUnavailableError, SourceTimeoutError, SourceRateLimitError, SourceAuthError, SourceParseError
from weather_bot.models.weather import WeatherCondition

BASE = "https://api.weatherapi.com"

FORECAST_RESPONSE = {
    "current": {
        "temp_c": 15.0, "feelslike_c": 13.0, "humidity": 60, "pressure_mb": 1013.0,
        "wind_kph": 18.0, "wind_degree": 270, "vis_km": 10.0, "uv": 3.0,
        "condition": {"code": 1000}, "precip_mm": 0.0, "cloud": 10,
    },
    "forecast": {
        "forecastday": [
            {
                "date": f"2026-05-{1 + i:02d}",
                "day": {
                    "maxtemp_c": 18.0, "mintemp_c": 10.0,
                    "daily_chance_of_rain": 10, "totalprecip_mm": 0.0,
                    "condition": {"code": 1000}, "maxwind_kph": 18.0,
                }
            }
            for i in range(7, 12)
        ]
    }
}


@pytest.mark.asyncio
@respx.mock
async def test_get_current_success():
    respx.get(f"{BASE}/v1/forecast.json").mock(return_value=httpx.Response(200, json=FORECAST_RESPONSE))
    reading = await WeatherAPISource("k").get_current(55.75, 37.62)
    assert reading.temperature_c == 15.0
    assert reading.wind_speed_ms == pytest.approx(18.0 / 3.6, abs=0.01)
    assert reading.condition == WeatherCondition.CLEAR


@pytest.mark.asyncio
@respx.mock
async def test_wind_speed_conversion():
    respx.get(f"{BASE}/v1/forecast.json").mock(return_value=httpx.Response(200, json=FORECAST_RESPONSE))
    reading = await WeatherAPISource("k").get_current(0, 0)
    assert reading.wind_speed_ms == pytest.approx(5.0, abs=0.01)


@pytest.mark.asyncio
@respx.mock
async def test_get_current_http_error():
    respx.get(f"{BASE}/v1/forecast.json").mock(return_value=httpx.Response(500))
    with pytest.raises(SourceUnavailableError):
        await WeatherAPISource("k").get_current(0, 0)


@pytest.mark.asyncio
@respx.mock
async def test_get_current_timeout():
    respx.get(f"{BASE}/v1/forecast.json").mock(side_effect=httpx.TimeoutException("t"))
    with pytest.raises(SourceTimeoutError):
        await WeatherAPISource("k").get_current(0, 0)


@pytest.mark.asyncio
@respx.mock
async def test_get_current_rate_limit():
    respx.get(f"{BASE}/v1/forecast.json").mock(return_value=httpx.Response(429))
    with pytest.raises(SourceRateLimitError):
        await WeatherAPISource("k").get_current(0, 0)


@pytest.mark.asyncio
@respx.mock
async def test_get_current_auth_error():
    respx.get(f"{BASE}/v1/forecast.json").mock(return_value=httpx.Response(401))
    with pytest.raises(SourceAuthError):
        await WeatherAPISource("k").get_current(0, 0)


@pytest.mark.asyncio
@respx.mock
async def test_get_current_malformed_json():
    respx.get(f"{BASE}/v1/forecast.json").mock(return_value=httpx.Response(200, json={}))
    with pytest.raises(SourceParseError):
        await WeatherAPISource("k").get_current(0, 0)


@pytest.mark.parametrize("code", [1000, 1003, 1006, 1009, 1030, 1063, 1066, 1069, 1087,
                                    1135, 1180, 1210, 1237, 1273])
def test_normalize_all_condition_codes(code):
    assert _code_to_condition(code) != WeatherCondition.UNKNOWN


@pytest.mark.asyncio
@respx.mock
async def test_get_forecast_returns_correct_days():
    respx.get(f"{BASE}/v1/forecast.json").mock(return_value=httpx.Response(200, json=FORECAST_RESPONSE))
    points = await WeatherAPISource("k").get_forecast(55.75, 37.62, days=5)
    assert len(points) == 5
