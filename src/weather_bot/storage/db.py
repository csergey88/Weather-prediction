import aiosqlite

from weather_bot.models.weather import Location


async def _get_db_path() -> str:
    from weather_bot.config import settings
    return settings.DB_PATH


async def init_db() -> None:
    db_path = await _get_db_path()
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_locations (
                telegram_id INTEGER PRIMARY KEY,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                city TEXT,
                country TEXT,
                timezone TEXT,
                updated_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
            )
        """)
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
        await db.execute("""
            CREATE TABLE IF NOT EXISTS weather_cache (
                cache_key TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                cached_at INTEGER NOT NULL
            )
        """)
        await db.commit()


async def save_user_location(telegram_id: int, location: Location) -> None:
    db_path = await _get_db_path()
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT INTO user_locations (telegram_id, lat, lon, city, country, timezone, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, strftime('%s', 'now'))
            ON CONFLICT(telegram_id) DO UPDATE SET
                lat = excluded.lat,
                lon = excluded.lon,
                city = excluded.city,
                country = excluded.country,
                timezone = excluded.timezone,
                updated_at = excluded.updated_at
            """,
            (telegram_id, location.lat, location.lon, location.city, location.country, location.timezone),
        )
        await db.commit()


async def get_user_location(telegram_id: int) -> Location | None:
    db_path = await _get_db_path()
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            "SELECT lat, lon, city, country, timezone FROM user_locations WHERE telegram_id = ?",
            (telegram_id,),
        ) as cursor:
            row = await cursor.fetchone()
    if row is None:
        return None
    return Location(lat=row[0], lon=row[1], city=row[2], country=row[3], timezone=row[4])
