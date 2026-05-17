from datetime import datetime, timezone

from weather_bot.models.forecast import AggregatedWeather, ForecastPoint
from weather_bot.models.weather import WeatherCondition

_CONDITION_EMOJI: dict[WeatherCondition, str] = {
    WeatherCondition.CLEAR: "☀️",
    WeatherCondition.PARTLY_CLOUDY: "🌤",
    WeatherCondition.CLOUDY: "⛅",
    WeatherCondition.OVERCAST: "☁️",
    WeatherCondition.RAIN: "🌧",
    WeatherCondition.DRIZZLE: "🌦",
    WeatherCondition.SNOW: "❄️",
    WeatherCondition.SLEET: "🌨",
    WeatherCondition.STORM: "⛈",
    WeatherCondition.FOG: "🌫",
    WeatherCondition.HAIL: "🌩",
    WeatherCondition.UNKNOWN: "🌡",
}

_WIND_DIRECTIONS = ["С", "ССВ", "СВ", "ВСВ", "В", "ВЮВ", "ЮВ", "ЮЮВ",
                    "Ю", "ЮЮЗ", "ЮЗ", "ЗЮЗ", "З", "ЗСЗ", "СЗ", "ССЗ"]

_SOURCE_ABBR = {
    "openweathermap": "OWM",
    "weatherapi": "WA",
    "accuweather": "ACW",
    "open_meteo": "OM",
}


def format_confidence_bar(confidence: float) -> str:
    filled = round(confidence * 5)
    bar = "█" * filled + "░" * (5 - filled)
    return f"{bar} {int(confidence * 100)}%"


def _wind_direction(deg: int) -> str:
    idx = round(deg / 22.5) % 16
    return _WIND_DIRECTIONS[idx]


def _time_ago(dt: datetime) -> str:
    now = datetime.now(timezone.utc)
    delta = now - dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else now - dt
    minutes = int(delta.total_seconds() / 60)
    if minutes < 1:
        return "только что"
    if minutes == 1:
        return "1 мин назад"
    if minutes < 60:
        return f"{minutes} мин назад"
    hours = minutes // 60
    return f"{hours} ч назад"


def format_current_weather(agg: AggregatedWeather) -> str:
    r = agg.current
    loc = agg.location
    emoji = _CONDITION_EMOJI.get(r.condition, "🌡")
    city_str = f"{loc.city}, {loc.country}" if loc.city and loc.country else (loc.city or f"{loc.lat:.2f}, {loc.lon:.2f}")

    date_str = r.fetched_at.strftime("%-d %B %Y, %H:%M")

    source_active = {reading.source for reading in agg.readings}
    source_status = "  ".join(
        f"{abbr} {'✓' if src in source_active else '✗'}"
        for src, abbr in _SOURCE_ABBR.items()
    )

    wind_dir = _wind_direction(r.wind_direction_deg)
    confidence = max((p.confidence for p in agg.forecast), default=0.0) if agg.forecast else 0.0

    lines = [
        f"{emoji} *{city_str}*",
        f"📅 {date_str}",
        "",
        f"🌡 Температура:   {r.temperature_c:+.0f}°C (ощущается {r.feels_like_c:+.0f}°C)",
        f"💧 Влажность:     {r.humidity_pct}%",
        f"💨 Ветер:         {wind_dir} {r.wind_speed_ms:.1f} м/с",
    ]
    if r.visibility_km is not None:
        lines.append(f"👁 Видимость:     {r.visibility_km:.0f} км")
    lines += [
        f"🌧 Осадки:        {r.precipitation_mm:.1f} мм/ч",
        f"☁️ Облачность:    {r.cloud_cover_pct}%",
        "",
        f"📊 Уверенность прогноза: {format_confidence_bar(confidence)}",
        f"🔄 Источники: {source_status}",
        f"⏱ Обновлено: {_time_ago(r.fetched_at)}",
    ]
    return "\n".join(lines)


def format_forecast(points: list[ForecastPoint], city: str) -> str:
    lines = [f"📅 *Прогноз для {city}*", ""]
    for p in points:
        emoji = _CONDITION_EMOJI.get(p.condition, "🌡")
        day = p.target_dt.strftime("%a %-d %b")
        lines.append(
            f"{day}: {emoji} {p.temperature_min_c:+.0f}..{p.temperature_max_c:+.0f}°C"
            f" | 💧 {p.precipitation_probability_pct}%"
            f" | 💨 {p.wind_speed_ms:.0f} м/с"
        )
    return "\n".join(lines)
