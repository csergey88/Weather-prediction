import asyncio
import time

import aiosqlite
from geopy.exc import GeocoderServiceError, GeocoderTimedOut
from geopy.geocoders import Nominatim

from weather_bot.models.weather import Location

_CACHE_TTL_S = 86400  # 24 hours
_MIN_REQUEST_INTERVAL_S = 1.0
_last_request_time: float = 0.0
_geocoder = Nominatim(user_agent="weather-prediction-bot/1.0")


class CityNotFoundError(Exception):
    pass


async def _get_db_path() -> str:
    from weather_bot.config import settings
    return settings.DB_PATH


async def _ensure_cache_table(db: aiosqlite.Connection) -> None:
    await db.execute("""
        CREATE TABLE IF NOT EXISTS geocode_cache (
            city_normalized TEXT PRIMARY KEY,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            city TEXT,
            country TEXT,
            cached_at INTEGER NOT NULL
        )
    """)
    await db.commit()


async def _get_cached(db: aiosqlite.Connection, city_normalized: str) -> Location | None:
    cutoff = int(time.time()) - _CACHE_TTL_S
    async with db.execute(
        "SELECT lat, lon, city, country FROM geocode_cache WHERE city_normalized = ? AND cached_at > ?",
        (city_normalized, cutoff),
    ) as cursor:
        row = await cursor.fetchone()
    if row:
        return Location(lat=row[0], lon=row[1], city=row[2], country=row[3])
    return None


async def _put_cached(db: aiosqlite.Connection, city_normalized: str, loc: Location) -> None:
    await db.execute(
        """
        INSERT OR REPLACE INTO geocode_cache (city_normalized, lat, lon, city, country, cached_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (city_normalized, loc.lat, loc.lon, loc.city, loc.country, int(time.time())),
    )
    await db.commit()


async def geocode(city: str) -> Location:
    global _last_request_time

    city_normalized = city.strip().lower()
    db_path = await _get_db_path()

    async with aiosqlite.connect(db_path) as db:
        await _ensure_cache_table(db)
        cached = await _get_cached(db, city_normalized)
        if cached:
            return cached

        # Rate limiting: max 1 req/sec to Nominatim
        now = time.monotonic()
        elapsed = now - _last_request_time
        if elapsed < _MIN_REQUEST_INTERVAL_S:
            await asyncio.sleep(_MIN_REQUEST_INTERVAL_S - elapsed)

        try:
            _last_request_time = time.monotonic()
            location = await asyncio.get_event_loop().run_in_executor(
                None, lambda: _geocoder.geocode(city, language="ru", addressdetails=True)
            )
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            raise CityNotFoundError(f"Geocoder error for '{city}': {e}") from e

        if location is None:
            raise CityNotFoundError(f"City not found: '{city}'")

        addr = location.raw.get("address", {})
        city_name = (
            addr.get("city")
            or addr.get("town")
            or addr.get("village")
            or addr.get("county")
            or city
        )
        country = addr.get("country")

        loc = Location(lat=location.latitude, lon=location.longitude, city=city_name, country=country)
        await _put_cached(db, city_normalized, loc)
        return loc
