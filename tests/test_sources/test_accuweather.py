import pytest
import respx
import httpx

from weather_bot.sources.accuweather import AccuWeatherSource, _icon_to_condition
from weather_bot.sources.base import SourceUnavailableError, SourceTimeoutError, SourceAuthError, SourceParseError
from weather_bot.models.weather import WeatherCondition

BASE = "https://dataservice.accuweather.com"

LOCATION_RESPONSE = {"Key": "328328", "LocalizedName": "Moscow"}

CURRENT_RESPONSE = [{
    "WeatherIcon": 1,
    "Temperature": {"Metric": {"Value": 15.0}},
    "RealFeelTemperature": {"Metric": {"Value": 13.0}},
    "RelativeHumidity": 60,
    "Pressure": {"Metric": {"Value": 1013.0}},
    "Wind": {"Speed": {"Metric": {"Value": 18.0}}, "Direction": {"Degrees": 270}},
    "Visibility": {"Metric": {"Value": 10.0}},
    "UVIndex": 3,
    "Precip1hr": {"Metric": {"Value": 0.0}},
    "CloudCover": 10,
}]

FORECAST_RESPONSE = {
    "DailyForecasts": [
        {
            "EpochDate": 1745712000 + i * 86400,
            "Temperature": {"Minimum": {"Value": 10.0}, "Maximum": {"Value": 18.0}},
            "Day": {"Icon": 1, "PrecipitationProbability": 10, "TotalLiquid": {"Value": 0.0},
                    "Wind": {"Speed": {"Value": 18.0}}},
        }
        for i in range(5)
    ]
}


@pytest.mark.asyncio
@respx.mock
async def test_get_current_success(tmp_db):
    respx.get(f"{BASE}/locations/v1/cities/geoposition/search").mock(
        return_value=httpx.Response(200, json=LOCATION_RESPONSE)
    )
    respx.get(f"{BASE}/currentconditions/v1/328328").mock(
        return_value=httpx.Response(200, json=CURRENT_RESPONSE)
    )
    reading = await AccuWeatherSource("k").get_current(55.75, 37.62)
    assert reading.temperature_c == 15.0
    assert reading.condition == WeatherCondition.CLEAR


@pytest.mark.asyncio
@respx.mock
async def test_get_current_http_error(tmp_db):
    respx.get(f"{BASE}/locations/v1/cities/geoposition/search").mock(
        return_value=httpx.Response(500)
    )
    with pytest.raises(SourceUnavailableError):
        await AccuWeatherSource("k").get_current(0, 0)


@pytest.mark.asyncio
@respx.mock
async def test_get_current_auth_error(tmp_db):
    respx.get(f"{BASE}/locations/v1/cities/geoposition/search").mock(
        return_value=httpx.Response(401)
    )
    with pytest.raises(SourceAuthError):
        await AccuWeatherSource("k").get_current(0, 0)


@pytest.mark.asyncio
@respx.mock
async def test_get_current_timeout(tmp_db):
    respx.get(f"{BASE}/locations/v1/cities/geoposition/search").mock(
        side_effect=httpx.TimeoutException("t")
    )
    with pytest.raises(SourceTimeoutError):
        await AccuWeatherSource("k").get_current(0, 0)


@pytest.mark.asyncio
@respx.mock
async def test_get_current_malformed_json(tmp_db):
    respx.get(f"{BASE}/locations/v1/cities/geoposition/search").mock(
        return_value=httpx.Response(200, json={})
    )
    with pytest.raises(SourceParseError):
        await AccuWeatherSource("k").get_current(0, 0)


@pytest.mark.asyncio
@respx.mock
async def test_location_key_cache_hit(tmp_db):
    loc_mock = respx.get(f"{BASE}/locations/v1/cities/geoposition/search").mock(
        return_value=httpx.Response(200, json=LOCATION_RESPONSE)
    )
    respx.get(f"{BASE}/currentconditions/v1/328328").mock(
        return_value=httpx.Response(200, json=CURRENT_RESPONSE)
    )
    src = AccuWeatherSource("k")
    await src.get_current(55.75, 37.62)  # first call
    await src.get_current(55.75, 37.62)  # second call — should use cache
    assert loc_mock.call_count == 1


@pytest.mark.parametrize("icon", list(range(1, 45)))
def test_normalize_all_condition_codes(icon):
    assert _icon_to_condition(icon) != WeatherCondition.UNKNOWN


@pytest.mark.asyncio
@respx.mock
async def test_get_forecast_returns_correct_days(tmp_db):
    respx.get(f"{BASE}/locations/v1/cities/geoposition/search").mock(
        return_value=httpx.Response(200, json=LOCATION_RESPONSE)
    )
    respx.get(f"{BASE}/forecasts/v1/daily/5day/328328").mock(
        return_value=httpx.Response(200, json=FORECAST_RESPONSE)
    )
    points = await AccuWeatherSource("k").get_forecast(55.75, 37.62, days=5)
    assert len(points) == 5
