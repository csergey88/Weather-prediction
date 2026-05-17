"""CLI demo — показывает форматированный прогноз на реалистичных данных."""
import asyncio
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "src")


def make_demo_data(city: str, days: int):
    from weather_bot.models.weather import Location, WeatherCondition, WeatherReading
    from weather_bot.models.forecast import AggregatedWeather, ForecastPoint

    now = datetime.now(timezone.utc)
    loc = Location(lat=55.75, lon=37.62, city=city, country="Россия")

    readings = [
        WeatherReading(source="open_meteo",      location=loc, fetched_at=now,
                       temperature_c=14.2, feels_like_c=11.8, humidity_pct=71,
                       pressure_hpa=1008.0, wind_speed_ms=5.1, wind_direction_deg=292,
                       visibility_km=9.0, condition=WeatherCondition.PARTLY_CLOUDY,
                       precipitation_mm=0.0, cloud_cover_pct=38),
        WeatherReading(source="openweathermap", location=loc, fetched_at=now,
                       temperature_c=13.8, feels_like_c=11.2, humidity_pct=73,
                       pressure_hpa=1007.5, wind_speed_ms=5.4, wind_direction_deg=285,
                       visibility_km=10.0, condition=WeatherCondition.PARTLY_CLOUDY,
                       precipitation_mm=0.0, cloud_cover_pct=42),
        WeatherReading(source="weatherapi",      location=loc, fetched_at=now,
                       temperature_c=14.5, feels_like_c=12.1, humidity_pct=69,
                       pressure_hpa=1008.2, wind_speed_ms=4.8, wind_direction_deg=300,
                       visibility_km=10.0, condition=WeatherCondition.CLOUDY,
                       precipitation_mm=0.0, cloud_cover_pct=55),
        WeatherReading(source="accuweather",     location=loc, fetched_at=now,
                       temperature_c=14.0, feels_like_c=11.5, humidity_pct=70,
                       pressure_hpa=1007.8, wind_speed_ms=5.0, wind_direction_deg=290,
                       visibility_km=9.5, condition=WeatherCondition.PARTLY_CLOUDY,
                       precipitation_mm=0.0, cloud_cover_pct=40),
    ]

    from weather_bot.aggregator.weights import normalize_weights
    from weather_bot.forecast.ensemble import weighted_average, majority_condition, compute_confidence

    weights = normalize_weights([r.source for r in readings])
    avg = weighted_average(readings, weights)
    cond = majority_condition(readings, weights)
    conf = compute_confidence(readings)

    current = WeatherReading(
        source="ensemble", location=loc, fetched_at=now,
        temperature_c=avg["temperature_c"], feels_like_c=avg["feels_like_c"],
        humidity_pct=int(avg["humidity_pct"]), pressure_hpa=avg["pressure_hpa"],
        wind_speed_ms=avg["wind_speed_ms"], wind_direction_deg=int(avg["wind_direction_deg"]),
        visibility_km=avg.get("visibility_km"), condition=cond,
        precipitation_mm=avg["precipitation_mm"], cloud_cover_pct=int(avg["cloud_cover_pct"]),
    )

    conditions = [WeatherCondition.CLOUDY, WeatherCondition.RAIN, WeatherCondition.PARTLY_CLOUDY,
                  WeatherCondition.CLEAR, WeatherCondition.CLEAR, WeatherCondition.CLEAR, WeatherCondition.PARTLY_CLOUDY]
    t_max = [15, 13, 14, 17, 19, 20, 18]
    t_min = [8,  7,  8,  9, 11, 12, 10]
    precip = [20, 65, 35, 10, 5, 5, 15]
    wind   = [5.1, 6.2, 4.8, 3.5, 3.0, 2.8, 4.0]

    forecast = [
        ForecastPoint(
            target_dt=now + timedelta(days=i),
            temperature_c=(t_max[i] + t_min[i]) / 2,
            temperature_min_c=float(t_min[i]),
            temperature_max_c=float(t_max[i]),
            precipitation_probability_pct=precip[i],
            precipitation_mm=0.0,
            condition=conditions[i],
            wind_speed_ms=wind[i],
            confidence=conf,
        )
        for i in range(min(days, 7))
    ]

    return AggregatedWeather(
        location=loc, aggregated_at=now, readings=readings,
        current=current, forecast=forecast,
        source_weights=weights, ensemble_version="v1_ridge",
    )


def main():
    city = sys.argv[1] if len(sys.argv) > 1 else "Москва"
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 3

    from weather_bot.bot.formatters import format_current_weather, format_forecast

    agg = make_demo_data(city, days)
    print("=" * 50)
    print(format_current_weather(agg))
    print()
    print("-" * 50)
    print()
    print(format_forecast(agg.forecast, city))
    print("=" * 50)
    print(f"\n[демо-режим: реальные источники заблокированы в sandbox-окружении]")
    print(f"Для запуска с реальными API: cp .env.example .env && python -m weather_bot.main")


if __name__ == "__main__":
    main()
