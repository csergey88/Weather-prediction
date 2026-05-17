from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from weather_bot.utils.geo import CityNotFoundError, geocode


@pytest.mark.asyncio
async def test_geocode_success(tmp_db):
    mock_location = MagicMock()
    mock_location.latitude = 55.75
    mock_location.longitude = 37.62
    mock_location.raw = {"address": {"city": "Москва", "country": "Россия"}}

    with patch("weather_bot.utils.geo._geocoder") as mock_geocoder:
        mock_geocoder.geocode.return_value = mock_location
        loc = await geocode("Москва")

    assert loc.lat == 55.75
    assert loc.lon == 37.62
    assert loc.city == "Москва"


@pytest.mark.asyncio
async def test_geocode_not_found(tmp_db):
    with patch("weather_bot.utils.geo._geocoder") as mock_geocoder:
        mock_geocoder.geocode.return_value = None
        with pytest.raises(CityNotFoundError):
            await geocode("xyzabc123")


@pytest.mark.asyncio
async def test_geocode_cache_hit(tmp_db):
    mock_location = MagicMock()
    mock_location.latitude = 55.75
    mock_location.longitude = 37.62
    mock_location.raw = {"address": {"city": "Москва", "country": "Россия"}}

    with patch("weather_bot.utils.geo._geocoder") as mock_geocoder:
        mock_geocoder.geocode.return_value = mock_location
        await geocode("Москва")  # first call — hits API
        await geocode("Москва")  # second call — should hit cache
        assert mock_geocoder.geocode.call_count == 1  # API called only once
